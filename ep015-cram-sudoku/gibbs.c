// EP015: CRAM focused Gibbs search (arXiv 2611.17309, App. C.3.1) in plain C, one CPU core per process.
// Reads: weights file (float32: W[729*729], B[729], mu[81], then float hbar, tau), puzzles on stdin (81 chars, '.' = empty).
// Writes one line per puzzle: solved(0/1) moves microseconds energy answer81
// Build: clang -O3 -march=native -o gibbs gibbs.c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include <time.h>

#define N 729
static float W[N * N], B[N], MU[81];
static float HBAR, TAU;
static uint64_t rs = 88172645463325252ULL;
static inline uint64_t xr(void) { rs ^= rs << 13; rs ^= rs >> 7; rs ^= rs << 17; return rs; }
static inline double ur(void) { return (xr() >> 11) * (1.0 / 9007199254740992.0); }

typedef struct { int x[81]; float H[N]; double E; } Chain;

static void init_chain(Chain *c, const int *q) {
    for (int i = 0; i < 81; i++) c->x[i] = q[i] >= 0 ? q[i] : (int)(xr() % 9);
    for (int k = 0; k < N; k++) c->H[k] = B[k];
    for (int j = 0; j < 81; j++) { const float *col = &W[(size_t)(j * 9 + c->x[j]) * N]; for (int k = 0; k < N; k++) c->H[k] += col[k]; }
    double e = 0; for (int i = 0; i < 81; i++) { int a = i * 9 + c->x[i]; e += 0.5 * (c->H[a] - B[a]) + B[a]; }
    c->E = e;
}

int main(int argc, char **argv) {
    if (argc < 5) { fprintf(stderr, "usage: gibbs weights.bin chains budget seed\n"); return 1; }
    FILE *f = fopen(argv[1], "rb");
    if (!f || fread(W, 4, N * N, f) != N * N || fread(B, 4, N, f) != N || fread(MU, 4, 81, f) != 81 ||
        fread(&HBAR, 4, 1, f) != 1 || fread(&TAU, 4, 1, f) != 1) { fprintf(stderr, "bad weights\n"); return 1; }
    fclose(f);
    // W is symmetric; store so that column (j*9+b) is contiguous: W[(j*9+b)*N + k] = W[k][j*9+b]
    int chains = atoi(argv[2]); long budget = atol(argv[3]); rs ^= (uint64_t)atoll(argv[4]) * 0x9E3779B97F4A7C15ULL; xr();
    Chain *C = malloc(sizeof(Chain) * chains);
    char line[256];
    const long period = 524288;
    while (fgets(line, sizeof line, stdin)) {
        if (strlen(line) < 81) continue;
        int q[81], freec[81], nf = 0;
        for (int i = 0; i < 81; i++) { q[i] = line[i] == '.' ? -1 : line[i] - '1'; if (q[i] < 0) freec[nf++] = i; }
        struct timespec t0, t1; clock_gettime(CLOCK_MONOTONIC, &t0);
        for (int c = 0; c < chains; c++) init_chain(&C[c], q);
        long moves = 0; int solved = -1; double bestE = 1e30; int best[81];
        for (long s = 0; s < budget && solved < 0; s++) {
            double T = HBAR * 0.40 * pow(0.31 / 0.40, (double)(s % period) / period);
            for (int c = 0; c < chains && solved < 0; c++) {
                Chain *ch = &C[c];
                if (ch->E <= TAU + 1e-3) { solved = c; break; }
                // focused cell: random free cell whose local energy exceeds its training mean by > 0.45 hbar
                int cand[81], nc = 0;
                for (int t = 0; t < nf; t++) { int i = freec[t]; if (ch->H[i * 9 + ch->x[i]] - MU[i] > 0.45f * HBAR) cand[nc++] = i; }
                int i = nc ? cand[xr() % nc] : freec[xr() % nf];
                float *h = &ch->H[i * 9]; float mn = h[0]; for (int a = 1; a < 9; a++) if (h[a] < mn) mn = h[a];
                double p[9], z = 0; for (int a = 0; a < 9; a++) { p[a] = exp(-(h[a] - mn) / T); z += p[a]; }
                double r = ur() * z; int nw = 8; for (int a = 0; a < 9; a++) { r -= p[a]; if (r <= 0) { nw = a; break; } }
                int old = ch->x[i]; moves++;
                if (nw != old) {
                    ch->E += h[nw] - h[old];
                    const float *cn = &W[(size_t)(i * 9 + nw) * N], *co = &W[(size_t)(i * 9 + old) * N];
                    for (int k = 0; k < N; k++) ch->H[k] += cn[k] - co[k];
                    ch->x[i] = nw;
                }
                if (ch->E < bestE) { bestE = ch->E; memcpy(best, ch->x, sizeof best); }
                if (ch->E <= TAU + 1e-3) { solved = c; }
            }
            if ((s & 4095) == 4095) for (int c = 0; c < chains; c++) init_chain(&C[c], C[c].x);  // exact recompute
        }
        clock_gettime(CLOCK_MONOTONIC, &t1);
        double us = (t1.tv_sec - t0.tv_sec) * 1e6 + (t1.tv_nsec - t0.tv_nsec) / 1e3;
        int *ans = solved >= 0 ? C[solved].x : best;
        printf("%d %ld %.1f %.6f ", solved >= 0, moves, us, solved >= 0 ? C[solved].E : bestE);
        for (int k = 0; k < 81; k++) putchar('1' + ans[k]);
        putchar('\n'); fflush(stdout);
    }
    return 0;
}
