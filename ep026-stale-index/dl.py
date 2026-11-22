import json, urllib.request, os
d = json.load(urllib.request.urlopen("https://huggingface.co/api/datasets/RealTimeData/bbc_news_alltime"))
files = [s['rfilename'] for s in d['siblings'] if s['rfilename'].endswith('.parquet')]
for f in files:
    out = "bbc/" + f.split('/')[0] + ".parquet"
    if os.path.exists(out): continue
    urllib.request.urlretrieve("https://huggingface.co/datasets/RealTimeData/bbc_news_alltime/resolve/main/" + f, out)
print("files", len(files))
