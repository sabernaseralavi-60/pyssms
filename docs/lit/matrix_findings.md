# What the matrix says

1. The closest open tool is SSMsOnPlane: vectorised functions on data frames for rectangles, with TTC, DRAC, MTTC, PSD, TAdv, a two-dimensional TTC and ACT. Its TAdv (source read) takes corner-to-corner intersections of the velocity lines with a 3-degree parallel rule, not the corner-side procedure of the 2010 appendix. It has no T2 or TG, no state hierarchy, no file readers (its README lists none) and no test against the appendix (none seen in the repository listing).
2. CommonRoad-CriMe is a criticality-measure toolbox for automated-vehicle scenarios in the CommonRoad format: a different setting (planning and scenarios), not a reader of the road-user data sets used in traffic-safety studies.
3. Traffic Intelligence is the established trajectory toolkit for road-safety studies; it was not tested here against the 2010 indicators.
4. The Emergency Index and ACT are separate two-dimensional measures, not the 2010 family.
5. None of the tools found provides TTC, TAdv, T2 and TG from one polygon together with the ten car-following measures and readers for SSAM, SUMO, VISSIM, LevelX and NGSIM. This is the gap, stated as "found no" for the searched sources.
6. The statement of need must therefore name SSMsOnPlane as existing open code for TAdv on rectangles; the earlier text (only a two-dimensional TTC repository) was incomplete.

Gap proof level: documented search of four sources plus source reading of the closest tool; not a systematic review. Novelty stays "to verify".
