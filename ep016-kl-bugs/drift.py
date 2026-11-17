"""EP016 lab 2: does the rounding matter in training? Distillation where the student STARTS as an exact copy of the teacher.
The true KL is 0 and the true gradient is exactly 0, so a correct loss must leave the student untouched.
Train with Adam (lr 1e-3, default eps 1e-8) for STEPS steps; measure parameter drift and the true (float64) KL
between student and teacher on held-out inputs. Conditions: naive FP32 F.kl_div, BF16 autocast F.kl_div, fixed FP32 (Amos 2026).
n = 3 seeds per condition. Writes lab/drift.jsonl.
"""
import copy, json, sys, time
import torch, torch.nn as nn, torch.nn.functional as F
sys.path.insert(0, __import__("os").path.dirname(__file__))
from audit import FwdKLFixed

torch.set_num_threads(4)
K, D, H, B, STEPS = 32000, 64, 256, 32, 300
OUT = open("lab/drift.jsonl", "w")


def make_teacher(seed):
    torch.manual_seed(seed)
    return nn.Sequential(nn.Linear(D, H), nn.GELU(), nn.Linear(H, K))


def loss_fn(name, zs, zt):
    if name == "naive_fp32":   # the standard distillation line
        return F.kl_div(F.log_softmax(zs, -1), F.log_softmax(zt, -1), reduction="batchmean", log_target=True)
    if name == "bf16":
        return F.kl_div(F.log_softmax(zs.bfloat16(), -1), F.log_softmax(zt.bfloat16(), -1), reduction="batchmean", log_target=True).float()
    if name == "fixed_fp32":
        return FwdKLFixed.apply(zs, zt).mean()


@torch.no_grad()
def true_kl(student, teacher, X):
    zt, zs = teacher(X).double(), student(X).double()
    lp, lq = F.log_softmax(zt, -1), F.log_softmax(zs, -1)
    return float((lp.exp() * (lp - lq)).sum(-1).mean())


def flat(m):
    return torch.cat([p.detach().flatten() for p in m.parameters()])


for seed in range(3):
    teacher = make_teacher(seed)
    for p in teacher.parameters(): p.requires_grad_(False)
    g = torch.Generator().manual_seed(1000 + seed)
    Xval = torch.randn(256, D, generator=g)
    for cond in ["naive_fp32", "bf16", "fixed_fp32"]:
        t0 = time.time()
        student = copy.deepcopy(teacher)
        for p in student.parameters(): p.requires_grad_(True)
        opt = torch.optim.Adam(student.parameters(), lr=1e-3)
        g2 = torch.Generator().manual_seed(2000 + seed)
        theta0 = flat(teacher)
        log = []
        for step in range(STEPS + 1):
            if step in (0, 1, 10, 30, 100, 300):
                log.append(dict(step=step, true_kl=true_kl(student, teacher, Xval),
                                drift=float((flat(student) - theta0).norm()), drift_rel=float((flat(student) - theta0).norm() / theta0.norm())))
            if step == STEPS: break
            X = torch.randn(B, D, generator=g2)
            with torch.no_grad(): zt = teacher(X)
            loss = loss_fn(cond, student(X), zt)
            opt.zero_grad(); loss.backward()
            if step == 0:
                gn = float(torch.sqrt(sum((p.grad.float() ** 2).sum() for p in student.parameters())))
            opt.step()
        row = dict(seed=seed, cond=cond, first_grad_norm=gn, log=log, secs=round(time.time() - t0, 1))
        OUT.write(json.dumps(row) + "\n"); OUT.flush()
        print(seed, cond, "grad0", f"{gn:.2e}", "final KL", f"{log[-1]['true_kl']:.2e}", "drift_rel", f"{log[-1]['drift_rel']:.2e}", row["secs"], "s", flush=True)
