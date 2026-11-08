"""Runs the code listing of the paper exactly as printed (plus timing) so that the output quoted in the text is real."""
import json, time
from pathlib import Path
t0 = time.time()
from pyssms import datasets, hierarchy, io, preprocessing, process, scenario, viz

traj = io.read_ngsim("data_raw/ngsim/Lankershim/vehicle-trajectory-data/0830am-0845am/trajectories-0830am-0845am.txt")
traj = preprocessing.smooth_trajectories(traj, window=5)
enc = process.encounters(traj, horizon=10.0)
h = hierarchy.build_hierarchy(enc)
print(h.table())
bank = datasets.load_conflict_bank("ngsim")
e = process.pair_series(bank.window(bank.select("B")[0]), 0, 1)
ax = viz.plot_indicator_profile(e)
m = scenario.following_measures(datasets.make("following"), leader=0, follower=1)
print({k: float(v[len(v)//2]) for k, v in m.items() if k != "t"})
out = {"n_enc": len(enc), "levels": h.levels, "totals": [int(x) for x in h.totals], "seconds": round(time.time() - t0, 1)}
Path("paper_softwarex/listing_result.json").write_text(json.dumps(out, indent=1))
print(out["seconds"], "s")
