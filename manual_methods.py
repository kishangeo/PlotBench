"""The 'Methods guide' chapter of the PlotBench manual: what each mathematical and statistical tool does, its equations, when to use it,
how to read the result, and a worked example. Every number in the examples is calculated here, at build time, with the same
libraries PlotBench uses, so the manual and the program always agree.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import numpy as np
import pandas as pd
from scipy import stats, signal

from plotbench import analysis as A


def _f(v, d=3):
    v = float(v)
    return f"{v:.{d}g}" if abs(v) >= 1e-3 or v == 0 else f"{v:.2e}"


def _tab(head, rows):
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table class='ref'><tr>{h}</tr>{b}</table>"


def _tool(title, what, eq, when, read, example, menu, anchor=None):
    a = f" id='{anchor}'" if anchor else ""
    return (f"<h3{a}>{title}</h3><p><b>What it does.</b> {what}</p>"
            + (f"<p><b>Equations.</b></p><div class='eqn'>{eq}</div>" if eq else "")
            + f"<p><b>When to use it.</b> {when}</p><p><b>How to read the result.</b> {read}</p>"
            + (f"<div class='example'><b>Worked example.</b> {example}</div>" if example else "")
            + f"<p class='menu'>Menu: {menu}</p>")


SIO2_A = np.array([51.2, 49.8, 50.6, 52.1, 50.9, 49.5, 51.7, 50.3])   # basalts, suite A
SIO2_B = np.array([53.0, 52.4, 54.1, 52.9, 53.6, 51.8, 53.3])         # basalts, suite B
SIO2_C = np.array([55.2, 54.0, 56.1, 55.4, 54.8, 55.9])               # basaltic andesites


def descriptive():
    x = SIO2_A; m, s = x.mean(), x.std(ddof=1)
    ex = (f"SiO<sub>2</sub> of eight basalts (wt%): {', '.join(map(str, x))}. Mean = {_f(m, 4)}, SD = {_f(s)}, standard error = "
          f"{_f(s / np.sqrt(len(x)))}, median = {_f(np.median(x), 4)}, IQR = {_f(stats.iqr(x))}, skewness = {_f(stats.skew(x, bias=False))}, "
          f"CV = {_f(100 * s / m)} %. The 95% confidence interval of the mean is {_f(m - stats.t.ppf(0.975, 7) * s / np.sqrt(8), 4)} to "
          f"{_f(m + stats.t.ppf(0.975, 7) * s / np.sqrt(8), 4)} wt%: if the sampling were repeated many times, 95% of such intervals would contain the true mean.")
    return _tool("Descriptive statistics",
                 "Summarises a column: centre (mean, median), spread (standard deviation, variance, range, interquartile range), shape (skewness, "
                 "kurtosis) and the precision of the mean (standard error, confidence interval).",
                 "mean x&#772; = &Sigma;x<sub>i</sub>/n &nbsp; | &nbsp; SD s = &radic;[&Sigma;(x<sub>i</sub> &minus; x&#772;)&sup2;/(n &minus; 1)] &nbsp; | &nbsp; "
                 "SE = s/&radic;n &nbsp; | &nbsp; 95% CI = x&#772; &plusmn; t<sub>0.975, n&minus;1</sub>&middot;SE &nbsp; | &nbsp; CV = 100 s/x&#772; &nbsp; | &nbsp; "
                 "skewness = [n/((n&minus;1)(n&minus;2))] &Sigma;((x<sub>i</sub> &minus; x&#772;)/s)&sup3;",
                 "Always, before any test. Report the median and IQR instead of mean and SD when the data are skewed or have outliers (trace elements, "
                 "grain sizes, concentrations near detection limits).",
                 "SD describes the scatter of the samples; SE describes how well the mean is known (it shrinks with more samples). Skewness near 0 = "
                 "symmetric; above +1 = long tail to high values (try a log scale). A CV of a few % is typical for replicate major-element analyses.",
                 ex, "Statistics &gt; Descriptive Statistics")


def correlation():
    rng = np.random.default_rng(4); mgo = np.array([12.1, 9.8, 8.4, 7.1, 6.0, 4.9, 3.8, 2.6, 1.9, 1.1])
    cao = 1.05 * mgo + 1.2 + rng.normal(0, 0.6, 10)
    r, p = stats.pearsonr(mgo, cao); rho, ps = stats.spearmanr(mgo, cao)
    ex = (f"MgO and CaO of ten lavas from one volcano: Pearson r = {_f(r)} (p = {_f(p)}), r&sup2; = {_f(r * r)}, Spearman &rho; = {_f(rho)}. "
          f"{_f(100 * r * r, 2)}% of the variance of CaO goes with MgO, as expected when olivine and clinopyroxene crystallise together.")
    return _tool("Correlation (Pearson, Spearman, partial)",
                 "Measures how strongly two columns vary together, from &minus;1 (one goes up as the other goes down) to +1.",
                 "Pearson r = &Sigma;(x<sub>i</sub> &minus; x&#772;)(y<sub>i</sub> &minus; y&#772;) / &radic;[&Sigma;(x<sub>i</sub> &minus; x&#772;)&sup2; &Sigma;(y<sub>i</sub> &minus; y&#772;)&sup2;]; "
                 "test: t = r&radic;(n &minus; 2)/&radic;(1 &minus; r&sup2;) with n &minus; 2 degrees of freedom. Spearman &rho; is Pearson's r of the ranks. "
                 "Partial r<sub>xy&middot;z</sub> = (r<sub>xy</sub> &minus; r<sub>xz</sub>r<sub>yz</sub>)/&radic;[(1 &minus; r<sub>xz</sub>&sup2;)(1 &minus; r<sub>yz</sub>&sup2;)].",
                 "Pearson for straight-line relations between roughly normal variables; Spearman for monotonic but curved relations, ranks, or data "
                 "with outliers; partial correlation to remove the effect of a third variable (e.g. two trace elements that both follow SiO<sub>2</sub>).",
                 "|r| above about 0.7 is strong, 0.3-0.7 moderate. The p-value says whether r could be zero by chance; with many samples a tiny r can be "
                 "'significant' but unimportant. Correlation is not causation. <b>Closed data:</b> oxides that sum to 100% are forced to correlate negatively "
                 "(if SiO<sub>2</sub> goes up, others must go down), so for compositions use ratios or log-ratios (clr) before reading too much into r.",
                 ex, "Statistics &gt; Correlation")


def normality():
    x = np.r_[SIO2_A, SIO2_B]; w, p = stats.shapiro(x); g = A.grubbs(np.r_[SIO2_A, 58.0]); gtxt = ""
    if g:
        gtxt = (f" Adding a value of 58.0 to suite A, Grubbs' test flags it: G = {_f(g[0]['G'])} against a critical value of {_f(g[0]['G critical'])} "
                f"(&alpha; = 0.05, n = 9).")
    ex = f"The 15 basalts of suites A and B together: Shapiro-Wilk W = {_f(w)}, p = {_f(p)}, so there is no evidence against normality.{gtxt}"
    return _tool("Normality tests, Q-Q plots and outliers",
                 "Check whether a column looks like a sample from a normal distribution, which t-tests, ANOVA and many regressions assume; find single "
                 "values that do not belong.",
                 "Shapiro-Wilk W = (&Sigma;a<sub>i</sub>x<sub>(i)</sub>)&sup2;/&Sigma;(x<sub>i</sub> &minus; x&#772;)&sup2; (ordered data against expected normal "
                 "order statistics); Kolmogorov-Smirnov D = max|F<sub>n</sub>(x) &minus; F(x)|; Anderson-Darling weights the tails more. "
                 "Grubbs G = max|x<sub>i</sub> &minus; x&#772;|/s, compared with a critical value from the t distribution.",
                 "Before parametric tests on small samples. Shapiro-Wilk is the most powerful for n below about 50; look at the Q-Q plot too "
                 "(Plot &gt; Statistical &gt; Q-Q Plot): points on the straight line = normal; a curve = skewed; S-shape = heavy tails.",
                 "p &lt; 0.05: the data are probably not normal: transform (log for concentrations) or use a nonparametric test. A large sample "
                 "can fail the test for tiny departures that do not matter, and a small sample can pass while being skewed: trust the plot. Only "
                 "remove an outlier with a reason (analytical problem, wrong sample); Grubbs assumes the rest is normal and tests one value at a time.",
                 ex, "Statistics &gt; Normality and Distributions")


def ttests():
    t, p = stats.ttest_ind(SIO2_A, SIO2_B, equal_var=False)
    sa, sb = SIO2_A.std(ddof=1), SIO2_B.std(ddof=1); na, nb = len(SIO2_A), len(SIO2_B)
    dfw = (sa ** 2 / na + sb ** 2 / nb) ** 2 / ((sa ** 2 / na) ** 2 / (na - 1) + (sb ** 2 / nb) ** 2 / (nb - 1))
    sp = np.sqrt(((na - 1) * sa ** 2 + (nb - 1) * sb ** 2) / (na + nb - 2)); d = (SIO2_B.mean() - SIO2_A.mean()) / sp
    u, pu = stats.mannwhitneyu(SIO2_A, SIO2_B)
    before = np.array([1.20, 0.95, 1.40, 1.10, 1.32, 0.88]); after = np.array([1.05, 0.90, 1.22, 1.01, 1.20, 0.85]); tp, pp = stats.ttest_rel(before, after)
    ex = (f"Suite A SiO<sub>2</sub> (mean {_f(SIO2_A.mean(), 4)}) against suite B (mean {_f(SIO2_B.mean(), 4)}): Welch t = {_f(t)}, "
          f"df = {_f(dfw)}, p = {_f(p)}; Cohen's d = {_f(d)} (a very large difference). Mann-Whitney U = {_f(u)}, p = {_f(pu)} gives the same "
          f"answer without assuming normality. Paired example: six standards measured before and after recalibration, paired t = {_f(tp)}, "
          f"p = {_f(pp)}: the recalibration lowered the values.")
    return _tool("t-tests and their nonparametric alternatives",
                 "Test whether a mean differs from a value (one-sample), whether two independent groups differ (two-sample) or whether paired "
                 "measurements changed (paired).",
                 "one-sample t = (x&#772; &minus; &mu;<sub>0</sub>)/(s/&radic;n); Student two-sample t = (x&#772;<sub>1</sub> &minus; x&#772;<sub>2</sub>)/[s<sub>p</sub>&radic;(1/n<sub>1</sub> + 1/n<sub>2</sub>)], "
                 "s<sub>p</sub>&sup2; = [(n<sub>1</sub>&minus;1)s<sub>1</sub>&sup2; + (n<sub>2</sub>&minus;1)s<sub>2</sub>&sup2;]/(n<sub>1</sub> + n<sub>2</sub> &minus; 2); "
                 "Welch t = (x&#772;<sub>1</sub> &minus; x&#772;<sub>2</sub>)/&radic;(s<sub>1</sub>&sup2;/n<sub>1</sub> + s<sub>2</sub>&sup2;/n<sub>2</sub>) with Welch-Satterthwaite df; "
                 "paired t = d&#772;/(s<sub>d</sub>/&radic;n) on the differences; effect size Cohen's d = (x&#772;<sub>2</sub> &minus; x&#772;<sub>1</sub>)/s<sub>p</sub>.",
                 "Two groups of roughly normal data. Prefer Welch's version (it does not assume equal variances and loses little when they are equal). "
                 "Use the paired test when the same samples or standards are measured twice. With skewed data or outliers use Mann-Whitney (independent) "
                 "or Wilcoxon signed-rank (paired), which compare ranks.",
                 "p &lt; 0.05: the means differ more than chance would explain. Report the difference with its confidence interval and the effect size, "
                 "not only p. A large p does not prove the means are equal; it may only mean there are too few samples (see Power and sample size).",
                 ex, "Statistics &gt; Compare Two Groups")


def anova():
    F, p = stats.f_oneway(SIO2_A, SIO2_B, SIO2_C); H, pk = stats.kruskal(SIO2_A, SIO2_B, SIO2_C); lv, pl = stats.levene(SIO2_A, SIO2_B, SIO2_C)
    allx = np.r_[SIO2_A, SIO2_B, SIO2_C]; ssb = sum(len(g) * (g.mean() - allx.mean()) ** 2 for g in (SIO2_A, SIO2_B, SIO2_C))
    ssw = sum(((g - g.mean()) ** 2).sum() for g in (SIO2_A, SIO2_B, SIO2_C)); eta = ssb / (ssb + ssw)
    ex = (f"SiO<sub>2</sub> of suites A, B and C: SS<sub>between</sub> = {_f(ssb)}, SS<sub>within</sub> = {_f(ssw)}, F(2, {len(allx) - 3}) = {_f(F)}, "
          f"p = {_f(p)}, &eta;&sup2; = {_f(eta)} ({_f(100 * eta, 2)}% of the variance lies between the suites). Levene's test p = {_f(pl)} "
          f"(equal variances are reasonable). Kruskal-Wallis H = {_f(H)}, p = {_f(pk)}. Tukey's test then shows which pairs differ.")
    return _tool("Analysis of variance (ANOVA) and Kruskal-Wallis",
                 "Tests whether three or more groups share the same mean, by comparing the variation between group means with the variation inside groups.",
                 "SS<sub>total</sub> = SS<sub>between</sub> + SS<sub>within</sub>; F = [SS<sub>between</sub>/(k &minus; 1)] / [SS<sub>within</sub>/(N &minus; k)]; "
                 "&eta;&sup2; = SS<sub>between</sub>/SS<sub>total</sub>. Tukey HSD compares every pair with the studentised range q = (x&#772;<sub>i</sub> &minus; x&#772;<sub>j</sub>)/&radic;(MS<sub>within</sub>/n). "
                 "Two-way ANOVA splits the variance into factor A, factor B and their interaction A&times;B. Kruskal-Wallis H = [12/(N(N+1))]&Sigma;R<sub>i</sub>&sup2;/n<sub>i</sub> &minus; 3(N + 1) on ranks.",
                 "Several groups (rock units, sites, treatments) of one measurement. Do not run many t-tests instead: with 5 groups there are 10 pairs and "
                 "the chance of at least one false 'significant' result rises to about 40%. Use two-way ANOVA for two factors (e.g. site and depth), "
                 "ANCOVA to remove a covariate, repeated-measures ANOVA or a mixed model when the same subjects are measured several times, and "
                 "Kruskal-Wallis + Dunn when the data are far from normal.",
                 "A small p says that at least one group differs; the post-hoc test (Tukey, Bonferroni or Dunn) says which. In two-way ANOVA read the "
                 "interaction first: if it is significant, the effect of one factor depends on the other and the main effects alone mislead.",
                 ex, "Statistics &gt; Compare Several Groups (ANOVA)")


def counts():
    tab = np.array([[18, 7], [6, 14]]); chi, p, dof, exp = stats.chi2_contingency(tab, correction=False); orr, pf = stats.fisher_exact(tab)
    ex = (f"Altered (rows: yes/no) against the presence of a fault within 100 m (columns): table [[18, 7], [6, 14]]. &chi;&sup2; = {_f(chi)}, "
          f"df = {dof}, p = {_f(p)}; the smallest expected count is {_f(exp.min())} (above 5, so the &chi;&sup2; test is valid). "
          f"Fisher exact p = {_f(pf)}, odds ratio = {_f(orr)}: alteration is about {_f(orr, 2)} times more likely near faults.")
    return _tool("Counts and proportions: chi-square, Fisher, McNemar, proportion tests",
                 "Tests whether two categorical variables are related, or whether proportions differ.",
                 "&chi;&sup2; = &Sigma;(O &minus; E)&sup2;/E, E = (row total &times; column total)/N, df = (r &minus; 1)(c &minus; 1); Fisher's exact test sums "
                 "hypergeometric probabilities of all tables at least as extreme; McNemar &chi;&sup2; = (b &minus; c)&sup2;/(b + c) for paired yes/no.",
                 "Counts in categories (rock type by locality, presence/absence). Use Fisher's exact test when any expected count is below 5 (small tables), "
                 "McNemar when the same items are classified twice.",
                 "p &lt; 0.05: the variables are associated. Look at which cells have O much larger than E (the standardised residuals) to see how.",
                 ex, "Statistics &gt; Counts, Proportions and Variances")


def regression():
    x = np.array([0, 2, 5, 10, 20, 40.]); y = np.array([0.004, 0.051, 0.122, 0.249, 0.502, 0.988]) + np.array([0, 0.003, -0.004, 0.002, -0.003, 0.004])
    res = stats.linregress(x, y); n = len(x); yhat = res.intercept + res.slope * x; s = np.sqrt(np.sum((y - yhat) ** 2) / (n - 2))
    x0 = 0.6; xc = (x0 - res.intercept) / res.slope
    ex = (f"A calibration of absorbance against concentration (0-40 ppm, six standards): slope b = {_f(res.slope, 4)} &plusmn; {_f(res.stderr)}, "
          f"intercept a = {_f(res.intercept)} &plusmn; {_f(res.intercept_stderr)}, R&sup2; = {_f(res.rvalue ** 2, 5)}, residual SD s = {_f(s)}. "
          f"A sample reading 0.600 has concentration x = (y &minus; a)/b = {_f(xc, 4)} ppm. Check the residual plot: a curve in the residuals means "
          f"a straight line is the wrong model (try a quadratic) even when R&sup2; is 0.999.")
    return _tool("Linear, polynomial and multiple regression",
                 "Fits y = a + bx (or a polynomial, or y = b<sub>0</sub> + b<sub>1</sub>x<sub>1</sub> + b<sub>2</sub>x<sub>2</sub> + ...) by least squares: the line "
                 "that makes the sum of squared vertical distances smallest.",
                 "b = &Sigma;(x<sub>i</sub> &minus; x&#772;)(y<sub>i</sub> &minus; y&#772;)/&Sigma;(x<sub>i</sub> &minus; x&#772;)&sup2;, a = y&#772; &minus; b x&#772;; "
                 "SE(b) = s/&radic;&Sigma;(x<sub>i</sub> &minus; x&#772;)&sup2;, s&sup2; = &Sigma;(y<sub>i</sub> &minus; &#375;<sub>i</sub>)&sup2;/(n &minus; 2); "
                 "R&sup2; = 1 &minus; SS<sub>res</sub>/SS<sub>tot</sub>, adjusted R&sup2; = 1 &minus; (1 &minus; R&sup2;)(n &minus; 1)/(n &minus; p &minus; 1). "
                 "Matrix form for multiple regression: &beta; = (X<sup>T</sup>X)<sup>&minus;1</sup>X<sup>T</sup>y, Cov(&beta;) = s&sup2;(X<sup>T</sup>X)<sup>&minus;1</sup>. "
                 "With a yErr column the fit is weighted, w<sub>i</sub> = 1/&sigma;<sub>i</sub>&sup2;, and reduced &chi;&sup2; = &Sigma;w<sub>i</sub>(y<sub>i</sub> &minus; &#375;<sub>i</sub>)&sup2;/(n &minus; p) "
                 "should be near 1 if the errors are right.",
                 "Calibration lines, trends, predicting one variable from others. Ordinary least squares assumes X is known exactly; when both "
                 "variables have errors of similar size (e.g. two measured ratios) use orthogonal distance regression or the York regression. "
                 "Multiple regression: check the variance inflation factor (VIF &gt; 5-10 = predictors too correlated: use PLS or PCA instead).",
                 "The slope and its standard error (or 95% CI) carry the answer; R&sup2; only says how much of the scatter the line explains. "
                 "Confidence band = where the true line lies; prediction band = where a new measurement will fall (wider). Always look at the residuals: "
                 "they should scatter evenly about zero with no pattern.",
                 ex, "Analysis &gt; Fitting &gt; Linear Fit / Polynomial Fit / Multiple Linear Regression")


def nonlinear():
    t = np.array([0, 1, 2, 4, 6, 8, 12, 16, 24.]); y = 100 * np.exp(-0.18 * t) + 5 + np.array([0.8, -1.1, 0.6, -0.4, 0.9, -0.7, 0.3, -0.5, 0.4])
    from scipy.optimize import curve_fit
    f = lambda t, A0, k, c: A0 * np.exp(-k * t) + c
    p, cov = curve_fit(f, t, y, p0=(90, 0.1, 0)); se = np.sqrt(np.diag(cov)); rss = np.sum((y - f(t, *p)) ** 2); n = len(t)
    aic = n * np.log(rss / n) + 2 * 3
    ex = (f"A decay measured at nine times, model y = A<sub>0</sub>e<sup>&minus;kt</sup> + c: A<sub>0</sub> = {_f(p[0])} &plusmn; {_f(se[0])}, "
          f"k = {_f(p[1])} &plusmn; {_f(se[1])} per hour, c = {_f(p[2])} &plusmn; {_f(se[2])}, half-life ln2/k = {_f(np.log(2) / p[1])} h, AIC = {_f(aic)}.")
    return _tool("Nonlinear curve fitting",
                 "Finds the parameters of any model y = f(x; p<sub>1</sub>, p<sub>2</sub>, ...) that minimise the (weighted) sum of squared residuals, by iteration "
                 "from starting values (Levenberg-Marquardt, or trust-region reflective when parameters have bounds).",
                 "minimise &chi;&sup2;(p) = &Sigma;w<sub>i</sub>[y<sub>i</sub> &minus; f(x<sub>i</sub>; p)]&sup2;; parameter covariance = s&sup2;(J<sup>T</sup>WJ)<sup>&minus;1</sup>, "
                 "J = &part;f/&part;p (Jacobian); AIC = n ln(RSS/n) + 2k, BIC = n ln(RSS/n) + k ln n for comparing models with k parameters.",
                 "Any physical law that is not a straight line: exponential decay or growth, Arrhenius, Michaelis-Menten, peaks, diffusion profiles, "
                 "dose-response. Choose the model from the physics, not from the best R&sup2;. Fix parameters you know, and give bounds to keep them physical.",
                 "Each parameter comes with a standard error; parameters that are strongly correlated (shown in the report) cannot be determined separately. "
                 "Compare models with AIC/BIC: lower is better, and a difference of more than about 2 is meaningful. If the fit wanders off, change the "
                 "starting values (the dialog shows the curve while you set them).",
                 ex, "Analysis &gt; Fitting &gt; Nonlinear Curve Fit (Ctrl+F)")


def errors_xy():
    return _tool("Errors in both variables: ODR and York regression",
                 "Straight-line fits when X and Y are both measured with errors (and the errors may be correlated), as for isotope ratios.",
                 "York et al. (2004): minimise S = &Sigma;W<sub>i</sub>(y<sub>i</sub> &minus; a &minus; bx<sub>i</sub>)&sup2; with "
                 "W<sub>i</sub> = &omega;(x<sub>i</sub>)&omega;(y<sub>i</sub>)/[&omega;(x<sub>i</sub>) + b&sup2;&omega;(y<sub>i</sub>) &minus; 2br<sub>i</sub>&radic;(&omega;(x<sub>i</sub>)&omega;(y<sub>i</sub>))], "
                 "&omega; = 1/&sigma;&sup2;, iterated for b; MSWD = S/(n &minus; 2).",
                 "Isochrons, calibrations against reference materials with uncertain values, any two measured quantities. Ordinary least squares here "
                 "gives a slope biased toward zero.",
                 "MSWD (mean square of weighted deviates) about 1 means the scatter matches the stated errors; much above 1 means extra (geological) "
                 "scatter, and the errors should be multiplied by &radic;MSWD; well below 1 means the errors are overestimated. The probability p of "
                 "the MSWD should be above 0.05 for a well-defined isochron.",
                 "The Pearson-York benchmark data give slope &minus;0.48053 &plusmn; 0.0580 and intercept 5.4799 &plusmn; 0.2950, exactly as published.",
                 "Analysis &gt; Fitting &gt; Orthogonal Distance Regression; Analysis &gt; Geochronology &gt; Isochron Age")


def pca_section():
    from plotbench import examples as EX
    df = EX.load("oxides"); cols = [c for c in ("SiO2", "TiO2", "Al2O3", "FeOt", "MgO", "CaO", "Na2O", "K2O") if c in df.columns]
    X = df[cols].apply(pd.to_numeric, errors="coerce").to_numpy(float); ev, pct, load, scores = A.pca(X)
    L = load * np.sqrt(ev)  # correlations of variables with components
    rows = [[c] + [_f(L[i, j], 2) for j in range(3)] for i, c in enumerate(cols)]
    top = lambda j, sign: ", ".join(cols[i] for i in np.argsort(sign * L[:, j])[::-1][:3])
    ex = (f"The eight major oxides of the example volcanic series (Help &gt; Example Data &gt; Major oxides), standardised. Eigenvalues: "
          f"{', '.join(_f(e, 3) for e in ev[:4])} ...; PC1 explains {_f(pct[0], 3)}% and PC2 {_f(pct[1], 3)}% of the variance (together "
          f"{_f(pct[0] + pct[1], 3)}%). Correlations of the oxides with the first three components:"
          + _tab(["Oxide", "PC1", "PC2", "PC3"], rows)
          + f"<p>PC1 contrasts {top(0, 1)} (positive) with {top(0, -1)} (negative): it is the differentiation trend from basalt to rhyolite. "
          f"Samples with high PC1 scores are evolved, low scores primitive. Only {sum(ev > 1)} eigenvalue(s) exceed 1, so by the Kaiser rule "
          f"{sum(ev > 1)} component(s) describe the data; the eight oxides vary essentially along one direction, as expected for one fractionating "
          f"magma series. A second, independent process (e.g. alteration moving Na<sub>2</sub>O and K<sub>2</sub>O) would show up as a separate component.</p>")
    return _tool("Principal component analysis (PCA)",
                 "Replaces many correlated columns by a few new, uncorrelated variables (principal components) that carry most of the variation. "
                 "PC1 is the direction in which the samples differ most, PC2 the next largest at right angles to it, and so on. It is the standard way "
                 "to look at many variables at once when an X-Y plot or a regression of one variable on another cannot show the structure, "
                 "as in machine learning and chemometrics.",
                 "Standardise each variable: z<sub>ij</sub> = (x<sub>ij</sub> &minus; x&#772;<sub>j</sub>)/s<sub>j</sub>. Correlation matrix R = Z<sup>T</sup>Z/(n &minus; 1); "
                 "R = V&Lambda;V<sup>T</sup> (eigenvectors V, eigenvalues &lambda;<sub>k</sub>, computed by singular value decomposition of Z). "
                 "Scores T = ZV (where each sample lies on each component); loadings = the columns of V; correlation of variable j with component k = "
                 "v<sub>jk</sub>&radic;&lambda;<sub>k</sub>; fraction of variance = &lambda;<sub>k</sub>/&Sigma;&lambda;.",
                 "Many variables measured on the same samples (major and trace elements, spectra, grain-size classes, survey answers) when you want to "
                 "see which samples resemble each other, which variables move together, how many independent processes are present, or to reduce "
                 "variables before regression or clustering. Standardising (the default) gives each variable equal weight regardless of its units. For "
                 "compositional data that sum to 100%, a centred log-ratio transform first (clr(x)<sub>j</sub> = ln(x<sub>j</sub>/g(x)), g = geometric mean of the "
                 "row; a column formula does it) avoids the spurious negative correlations of closed data. Rows with a missing value are left out.",
                 "<b>Scree plot</b>: keep the components before the 'elbow', or those with eigenvalue &gt; 1 (Kaiser). <b>Score plot</b>: samples close together "
                 "are similar; separate clusters = different populations (colour them by group to test an idea); outliers sit far from the rest. "
                 "<b>Loading plot / correlation circle</b>: arrows pointing the same way = positively correlated variables, opposite = negatively "
                 "correlated, at right angles = unrelated; a long arrow near the circle is well represented by these two components. <b>Biplot</b>: "
                 "samples lie toward the arrows of the variables they are rich in. Components are mathematical directions, not processes: you name them "
                 "from the loadings (e.g. 'fractionation', 'alteration'), and their signs are arbitrary.",
                 ex, "Statistics &gt; Multivariate &gt; Principal Component Analysis (makes the scree plot and biplot); Plot &gt; Multivariate (PCA) for "
                 "score, loading, biplot and scree graphs of any columns", anchor="pca")


def multivariate_others():
    out = _tool("Discriminant analysis (LDA, QDA)",
                "Finds the combinations of variables that best separate known groups, then assigns new samples to a group.",
                "LDA: maximise between-group over within-group variance, w = S<sub>W</sub><sup>&minus;1</sup>(&mu;<sub>1</sub> &minus; &mu;<sub>2</sub>) for two groups; "
                "a sample goes to the group with the largest posterior probability. QDA allows each group its own covariance matrix.",
                "Classifying samples with known training groups (tectonic setting from trace elements, provenance, facies). Needs more samples per group "
                "than variables.",
                "The classification table (confusion matrix) and the cross-validated accuracy say how well the groups can be told apart; the "
                "coefficients say which variables matter. Discriminant diagrams in the literature (e.g. Pearce granite diagrams) were made this way.",
                "", "Statistics &gt; Multivariate and Clustering &gt; Discriminant Analysis")
    out += _tool("Clustering: k-means and hierarchical",
                 "Groups samples without knowing groups in advance.",
                 "k-means minimises &Sigma;<sub>clusters</sub>&Sigma;<sub>i</sub>||z<sub>i</sub> &minus; &mu;<sub>c</sub>||&sup2; (within-cluster sum of squares) "
                 "on standardised variables; hierarchical clustering merges the two closest clusters step by step (Ward's method merges the pair that "
                 "increases the within-cluster variance least) and draws the dendrogram.",
                 "Exploring whether samples fall into natural families (e.g. several magma batches, source areas). Run PCA first to see the structure; "
                 "cluster on standardised variables.",
                 "k-means needs k: try several and look for the 'elbow' in the within-cluster sum of squares. In the dendrogram, cut where the "
                 "vertical distances become long: those are well-separated clusters. Clusters always come out, even from random data: check that they "
                 "make geological sense.",
                 "", "Statistics &gt; Multivariate and Clustering")
    out += _tool("MANOVA and MANCOVA",
                 "ANOVA for several response variables at once.",
                 "Wilks' &Lambda; = |W|/|W + B| (W, B = within- and between-group sums-of-squares-and-products matrices), with Pillai's trace and "
                 "Hotelling-Lawley as alternatives, converted to approximate F.",
                 "Do groups differ in their overall composition (several elements together) rather than one element at a time.",
                 "A small p says the group mean vectors differ; then use discriminant analysis or univariate ANOVAs to see in which variables.",
                 "", "Statistics &gt; Multivariate and Clustering")
    return out


def models():
    out = _tool("Logistic regression and generalised linear models (GLM)",
                "Regression for outcomes that are not normal: yes/no (logistic), counts (Poisson), positive skewed values (gamma).",
                "logit(p) = ln[p/(1 &minus; p)] = b<sub>0</sub> + b<sub>1</sub>x<sub>1</sub> + ...; GLM: g(E[y]) = X&beta; with a link function g, fitted by maximum "
                "likelihood; odds ratio = e<sup>b</sup>.",
                "Presence/absence of a mineral or deposit against geochemical variables; numbers of events; any outcome bounded at 0 or 1.",
                "An odds ratio of 2 means each unit of x doubles the odds of 'yes'. Check deviance and AIC; the ROC curve gives the classification skill.",
                "", "Statistics &gt; Regression and Models")
    out += _tool("PLS regression",
                 "Predicts y from many strongly correlated predictors (spectra, many elements) by building a few latent components that both summarise X "
                 "and correlate with y.",
                 "X = TP<sup>T</sup> + E, y = Tq + f, with components chosen to maximise cov(Xw, y); VIP scores rank the predictors.",
                 "More predictors than samples, or predictors that are nearly collinear (where multiple regression fails): calibrating concentrations from "
                 "spectra, predicting a property from a whole analysis.",
                 "Choose the number of components by cross-validation (the error stops falling); VIP &gt; 1 marks the important predictors.",
                 "", "Statistics &gt; Regression and Models &gt; PLS Regression")
    out += _tool("Linear mixed models",
                 "Regression with random effects for grouped or repeated data (several analyses per sample, several samples per outcrop).",
                 "y = X&beta; + Zu + &epsilon;, u ~ N(0, G), &epsilon; ~ N(0, R); fitted by restricted maximum likelihood (REML).",
                 "When observations are not independent: spots within grains, grains within samples, samples within sites. Treating them as "
                 "independent overstates the certainty.",
                 "Fixed effects read like ordinary regression coefficients; the variance components say how much variation lies at each level "
                 "(e.g. between samples versus within samples).",
                 "", "Statistics &gt; Regression and Models")
    return out


def diagnostics():
    a = np.array([10.2, 12.5, 9.8, 15.1, 11.0, 13.4, 8.9, 14.2]); b = a + np.array([0.3, 0.6, 0.1, 0.9, 0.2, 0.5, 0.0, 0.7])
    d = b - a; ex = (f"Eight samples by two methods: mean difference (bias) = {_f(d.mean())}, limits of agreement = {_f(d.mean() - 1.96 * d.std(ddof=1))} to "
                     f"{_f(d.mean() + 1.96 * d.std(ddof=1))}: method B reads {_f(d.mean())} higher on average, and 95% of single differences lie within those limits.")
    out = _tool("Bland-Altman agreement",
                "Compares two measurement methods on the same samples.",
                "differences d<sub>i</sub> = b<sub>i</sub> &minus; a<sub>i</sub> plotted against means (a<sub>i</sub> + b<sub>i</sub>)/2; bias = d&#772;; limits of agreement = d&#772; &plusmn; 1.96 s<sub>d</sub>.",
                "Method comparison (XRF against ICP-MS, two laboratories). A correlation coefficient is the wrong tool here: two methods can correlate "
                "perfectly and still disagree.",
                "If the limits of agreement are narrower than the precision you need, the methods are interchangeable. A slope in the plot means the "
                "difference depends on concentration.", ex, "Statistics &gt; Survival, Diagnostics and Reliability &gt; Bland-Altman")
    out += _tool("Kaplan-Meier survival, Cox regression, ROC, Cronbach's alpha",
                 "Time-to-event data with censoring (Kaplan-Meier, Cox), classification skill (ROC) and internal consistency of a questionnaire scale (alpha).",
                 "Kaplan-Meier S(t) = &Pi;<sub>t<sub>i</sub>&le;t</sub>(1 &minus; d<sub>i</sub>/n<sub>i</sub>); log-rank test compares curves; Cox h(t) = h<sub>0</sub>(t)e<sup>&beta;x</sup> "
                 "(hazard ratio e<sup>&beta;</sup>); ROC: true-positive against false-positive rate for every cut-off, AUC = area under it; Cronbach "
                 "&alpha; = [k/(k &minus; 1)](1 &minus; &Sigma;s<sub>i</sub>&sup2;/s<sub>total</sub>&sup2;).",
                 "Lifetimes of equipment or samples that are still 'alive' at the end (censored); how well a score separates two classes; reliability "
                 "of a multi-item scale.",
                 "AUC 0.5 = no skill, above 0.8 = good; hazard ratio 2 = twice the risk per unit; &alpha; above 0.7 is usually acceptable.",
                 "", "Statistics &gt; Survival, Diagnostics and Reliability")
    from scipy.stats import norm
    n = 2 * ((norm.ppf(0.975) + norm.ppf(0.8)) / 0.8) ** 2
    out += _tool("Power and sample size",
                 "How many samples you need to detect a difference of a given size, or how likely you were to detect it with the samples you have.",
                 "two-sample t-test, approximately n per group = 2[(z<sub>1&minus;&alpha;/2</sub> + z<sub>1&minus;&beta;</sub>)/d]&sup2;, d = &delta;/&sigma; (effect size).",
                 "Before a field campaign or experiment, and when a test was not significant (was the study big enough to find anything?).",
                 "Power 0.8 is the usual target: an 80% chance of finding a real effect of the stated size.",
                 f"To detect an effect of 0.8 standard deviations with &alpha; = 0.05 and power 0.8 needs about {int(np.ceil(n))} samples per group "
                 "(the exact t-based value in PlotBench is one or two more).", "Statistics &gt; Power and Sample Size")
    return out


def signal_section():
    fs, T = 100.0, 4.0; t = np.arange(0, T, 1 / fs); y = np.sin(2 * np.pi * 5 * t) + 0.5 * np.sin(2 * np.pi * 12 * t)
    fq, amp, _ = A.fft(t, y); top = fq[np.argsort(amp)[::-1][:2]]
    out = _tool("Smoothing (Savitzky-Golay, moving average, median)",
                "Reduces noise. A moving average replaces each point by the mean of a window; a median filter by the median (removes spikes); "
                "Savitzky-Golay fits a low-order polynomial to each window and keeps peak heights and widths much better.",
                "moving average y&#771;<sub>i</sub> = (1/m)&Sigma;<sub>j</sub>y<sub>i+j</sub>; Savitzky-Golay y&#771;<sub>i</sub> = &Sigma;<sub>j</sub>c<sub>j</sub>y<sub>i+j</sub> with "
                "coefficients c<sub>j</sub> from a least-squares polynomial of order p over the window m. The same coefficients give smoothed derivatives.",
                "Noisy spectra and time series before reading peak positions; median for spikes (cosmic rays in Raman).",
                "A window wider than the narrowest real feature distorts it: keep the window below about half the peak width. Fit raw data whenever "
                "possible; smooth for display and for finding peaks.", "", "Analysis &gt; Signal Processing &gt; Smooth")
    out += _tool("Fourier transform (FFT) and filters",
                 "Splits a signal into its frequencies.",
                 "X<sub>k</sub> = &Sigma;<sub>n=0</sub><sup>N&minus;1</sup>x<sub>n</sub>e<sup>&minus;2&pi;ikn/N</sup>; frequencies k/(N&Delta;t) up to the Nyquist "
                 "frequency 1/(2&Delta;t); amplitude 2|X<sub>k</sub>|/N; resolution 1/(N&Delta;t). Butterworth filters have a maximally flat pass band; "
                 "PlotBench filters forwards and backwards (zero phase), so peaks do not shift.",
                 "Periodic signals, vibration, tides, cyclostratigraphy; removing high-frequency noise or a slow drift.",
                 "Peaks in the amplitude spectrum are the dominant periods (period = 1/frequency). Data must be evenly spaced (interpolate first). A "
                 "longer record gives finer frequency resolution; a finer sampling interval reaches higher frequencies.",
                 f"A 4 s record sampled at 100 Hz of sin(2&pi;&middot;5t) + 0.5 sin(2&pi;&middot;12t): the two largest peaks are at {_f(top[0], 3)} and {_f(top[1], 3)} Hz, "
                 f"with amplitudes 1 and 0.5; the resolution is 1/4 s = 0.25 Hz and the Nyquist frequency 50 Hz.",
                 "Analysis &gt; Signal Processing")
    out += _tool("Wavelets, spectrogram, Hilbert envelope, correlation",
                 "Frequency content that changes with time (spectrogram = FFT in sliding windows; continuous wavelet transform = scalogram), the envelope "
                 "of an oscillation (Hilbert transform), and the similarity of two signals at different lags (cross-correlation).",
                 "CWT W(a, b) = (1/&radic;a)&int;x(t)&psi;*((t &minus; b)/a)dt; analytic signal x + iH[x], envelope = |x + iH[x]|; "
                 "cross-correlation r<sub>xy</sub>(&tau;) = &Sigma;x<sub>t</sub>y<sub>t+&tau;</sub>/&radic;(&Sigma;x&sup2;&Sigma;y&sup2;).",
                 "Signals whose period drifts (climate records, chirps), amplitude modulation, finding the delay between two records.",
                 "Bright areas of the scalogram = strong oscillation at that period and time; the lag of the highest cross-correlation is the delay.",
                 "", "Analysis &gt; Signal Processing")
    out += _tool("Differentiation, integration and interpolation",
                 "Slope, area under the curve and values between the data points.",
                 "central difference dy/dx &asymp; (y<sub>i+1</sub> &minus; y<sub>i&minus;1</sub>)/(x<sub>i+1</sub> &minus; x<sub>i&minus;1</sub>); trapezoid area = "
                 "&Sigma;(x<sub>i+1</sub> &minus; x<sub>i</sub>)(y<sub>i</sub> + y<sub>i+1</sub>)/2; cubic spline: piecewise cubics with continuous first and second derivatives.",
                 "Rates (heating rate, growth rate), peak areas, resampling to a common X before subtracting or averaging curves.",
                 "Derivatives amplify noise: smooth first or use the Savitzky-Golay derivative. A spline can overshoot between widely spaced points; "
                 "linear interpolation never does.", "", "Analysis &gt; Mathematics")
    return out


def spectro_section():
    from math import log, sqrt, pi
    return _tool("Peak shapes, baselines and deconvolution",
                 "Separates overlapping peaks into components after removing the background, and reports each peak's centre, height, width and area.",
                 "Gaussian G(x) = h exp[&minus;4 ln2 (x &minus; x<sub>0</sub>)&sup2;/w&sup2;], area = hw&radic;(&pi;/(4 ln 2)) = 1.0645hw; Lorentzian "
                 "L(x) = h/[1 + 4(x &minus; x<sub>0</sub>)&sup2;/w&sup2;], area = &pi;hw/2; pseudo-Voigt = &eta;L + (1 &minus; &eta;)G; Voigt = Gaussian &otimes; "
                 "Lorentzian (w = FWHM). Baselines: ALS minimises &Sigma;w<sub>i</sub>(y<sub>i</sub> &minus; z<sub>i</sub>)&sup2; + &lambda;&Sigma;(&Delta;&sup2;z<sub>i</sub>)&sup2; with small weights "
                 "for points above z (Eilers &amp; Boelens 2005); Shirley B(x) = I<sub>right</sub> + (I<sub>left</sub> &minus; I<sub>right</sub>)A<sub>beyond x</sub>/A<sub>total</sub>, iterated.",
                 "Raman, FTIR, XRD, XPS, chromatography. Lorentzian for natural line shapes (gases, XPS core levels before broadening), Gaussian for "
                 "instrument-dominated or disordered broadening, pseudo-Voigt/Voigt for the usual mixture. ALS for fluorescence backgrounds; Shirley for "
                 "XPS steps; anchor points when you know where the background is.",
                 "Report areas (not heights) for quantities proportional to amount. A fit with more peaks always looks better: add a peak only when the "
                 "residual shows a systematic shoulder, and fix widths or positions that physics constrains (doublets, known bands).",
                 f"For the same height and FWHM, a Lorentzian has {pi / 2 / sqrt(pi / (4 * log(2))):.3f} times the area of a Gaussian, because of its long tails.",
                 "Analysis &gt; Peak Analyzer (Ctrl+Shift+K)")


def geo_section():
    out = _tool("Mineral formulae, Fe<sup>3+</sup> and the CIPW norm",
                "Mineral formula: oxide wt% &rarr; cations per formula unit on a fixed number of oxygens. CIPW norm: a rock analysis &rarr; the ideal "
                "anhydrous minerals that would crystallise from it.",
                "moles of oxide m<sub>j</sub> = wt%<sub>j</sub>/M<sub>j</sub>; oxygens O = &Sigma;m<sub>j</sub>o<sub>j</sub>; cations per N oxygens = m<sub>j</sub>c<sub>j</sub>N/O. "
                "Droop (1987): Fe<sup>3+</sup> = 2N(1 &minus; T/S), T = ideal cations, S = cations summed with all Fe as Fe<sup>2+</sup>. The norm allocates the "
                "molecular proportions in a fixed order (apatite, ilmenite, orthoclase, albite, anorthite ...) and, if silica runs short, converts "
                "hypersthene to olivine, albite to nepheline and so on.",
                "Formulae for every microprobe analysis (check of quality: cation sums near ideal); the norm to classify fine-grained or glassy rocks, "
                "to see silica saturation (quartz-, hypersthene- or nepheline-normative) and for the differentiation index.",
                "Cation sums far from ideal mean a bad analysis or the wrong mineral. Fe<sup>3+</sup> from charge balance is only as good as the analysis "
                "(&plusmn;1% on the total moves it a lot). Normative minerals are not the minerals present.",
                "", "Column &gt; Mineral Formula from Oxides; Column &gt; CIPW Norm")
    out += _tool("Thermometers, barometers and the coupled P-T solver",
                 "Temperature and pressure from element exchange or solubility between minerals (and melts), calibrated on experiments.",
                 "Most calibrations have the form ln K = &minus;&Delta;H/RT + &Delta;S/R &minus; P&Delta;V/RT, i.e. T = (a + bP)/(c &minus; ln K) or "
                 "P = (&minus;a + T(c &minus; ln K))/b. When a thermometer needs P and a barometer needs T, the solver iterates T<sub>n</sub> = f<sub>T</sub>(P<sub>n</sub>), "
                 "P<sub>n+1</sub> = f<sub>P</sub>(T<sub>n</sub>) until P changes by less than 0.01 kbar; it converges because thermometers depend only weakly on P.",
                 "Use only the calibration made for your assemblage and range (the dialog says which). Check equilibrium first: Fe-Mg K<sub>D</sub> tests "
                 "(olivine-liquid 0.30 &plusmn; 0.03, clinopyroxene-liquid 0.28 &plusmn; 0.08) and textures. Average several mineral pairs.",
                 "Quote the calibration error (given for each method; typically &plusmn;30-60 &deg;C and &plusmn;1.5-5 kbar), not the analytical precision. "
                 "Results outside the calibration range are blank or should be treated as unreliable.",
                 "The garnet-orthopyroxene barometers run on the 12 garnet-lherzolite experiments of Brey et al. (1990): Brey &amp; K&ouml;hler P<sub>BKN</sub> "
                 "+0.1 &plusmn; 2.6 kbar from the run pressures; Putirka (2008) liquid and clinopyroxene components reproduce his Tables 1 and 3 exactly.",
                 "Column &gt; Thermobarometry; Column &gt; Coupled P-T Solver")
    out += _tool("Geochronology: isochrons, concordia, weighted means and age spectra",
                 "Ages from radioactive decay and the statistics that say whether a set of analyses records one event.",
                 "decay: D* = P(e<sup>&lambda;t</sup> &minus; 1), so on an isochron D/D<sub>ref</sub> = (D/D<sub>ref</sub>)<sub>0</sub> + (P/D<sub>ref</sub>)(e<sup>&lambda;t</sup> &minus; 1) and "
                 "t = ln(1 + slope)/&lambda;. U-Pb: <sup>206</sup>Pb*/<sup>238</sup>U = e<sup>&lambda;238 t</sup> &minus; 1, <sup>207</sup>Pb*/<sup>235</sup>U = e<sup>&lambda;235 t</sup> &minus; 1; "
                 "concordia age minimises S(t) = R<sup>T</sup>&Omega;R (Ludwig 1998). Weighted mean x&#772; = &Sigma;(x<sub>i</sub>/&sigma;<sub>i</sub>&sup2;)/&Sigma;(1/&sigma;<sub>i</sub>&sup2;), "
                 "&sigma;<sub>x&#772;</sub> = 1/&radic;&Sigma;(1/&sigma;<sub>i</sub>&sup2;), MSWD = &Sigma;(x<sub>i</sub> &minus; x&#772;)&sup2;/&sigma;<sub>i</sub>&sup2;/(n &minus; 1). "
                 "KDE f(t) = (1/nh)&Sigma;K((t &minus; t<sub>i</sub>)/h), bandwidth h by least-squares cross-validation; PDP = mean of normal curves N(t<sub>i</sub>, &sigma;<sub>i</sub>).",
                 "Isochrons for cogenetic samples or minerals; concordia for zircon, monazite, titanite U-Pb; weighted means for a population thought "
                 "to be one age; KDE for detrital (many-age) populations; cumulative distributions to compare samples.",
                 "MSWD near 1 (p &gt; 0.05): one population within error; MSWD &gt;&gt; 1: extra scatter (inheritance, Pb loss, open system), so the "
                 "age error must be expanded or the data split. Discordant analyses (more than a few %) are usually excluded from age calculations. "
                 "The PDP over-weights precise analyses and makes narrow spikes; the KDE shows the population shape more fairly.",
                 "", "Analysis &gt; Geochronology; Plot &gt; Geochronology")
    return out


def choosing():
    rows = [("Summarise one variable", "Descriptive statistics, histogram, box plot", "Median and IQR if skewed"),
            ("Is it normal?", "Shapiro-Wilk + Q-Q plot", "Log-transform concentrations"),
            ("Two groups differ?", "Welch t-test", "Mann-Whitney"),
            ("Same samples measured twice?", "Paired t-test", "Wilcoxon signed-rank"),
            ("Three or more groups?", "One-way ANOVA + Tukey", "Kruskal-Wallis + Dunn"),
            ("Two factors?", "Two-way ANOVA", "Aligned ranks or GLM"),
            ("Repeated or nested data?", "Linear mixed model", "Repeated-measures ANOVA"),
            ("Two variables related?", "Pearson r + linear fit", "Spearman &rho;"),
            ("Predict y from x", "Linear or nonlinear fit", "ODR/York if x has errors"),
            ("Predict y from many x", "Multiple regression", "PLS when x are collinear"),
            ("Yes/no outcome", "Logistic regression", "Fisher exact for a 2&times;2 table"),
            ("Categories related?", "Chi-square", "Fisher exact (small counts)"),
            ("Many variables: what is the structure?", "PCA (scores, loadings, biplot)", "Clustering"),
            ("Assign samples to known groups", "Discriminant analysis", "Classification diagrams"),
            ("Two methods agree?", "Bland-Altman", "Paired t-test on differences"),
            ("Overlapping peaks", "Peak Analyzer (baseline + fit)", "Derivative spectra to find shoulders"),
            ("Periodic signal", "FFT", "Wavelet scalogram if the period drifts"),
            ("One age from many analyses", "Weighted mean / concordia age", "Check MSWD and p")]
    return "<h3>Which tool for which question</h3>" + _tab(["Question", "First choice", "Alternative / check"], rows)


def chapter():
    css = ("<style>.eqn { background: #f6f7fb; border-left: 3px solid #7a8bb5; padding: 4px 8px; margin: 4px 0; font-family: 'Cambria Math', 'Times New Roman'; } "
           ".example { background: #fbf7ee; border: 1px solid #e3d7b8; padding: 6px; margin: 4px 0; } .menu { color: #555; font-size: 9pt; }</style>")
    intro = ("<p>This chapter explains every mathematical and statistical tool in PlotBench: what it does, the equations it uses, when it is "
             "the right tool (and when it is not), how to read its result, and a worked example. The examples are calculated with the same code "
             "as the program when this manual is built, so you can reproduce them. Statistics answer questions about uncertainty; they never "
             "replace looking at the data in a graph first.</p>")
    parts = [choosing(), "<h3 style='color:#16325c'>Describing data</h3>", descriptive(), correlation(), normality(),
             "<h3 style='color:#16325c'>Comparing groups</h3>", ttests(), anova(), counts(),
             "<h3 style='color:#16325c'>Fitting and regression</h3>", regression(), nonlinear(), errors_xy(), models(),
             "<h3 style='color:#16325c'>Many variables at once</h3>", pca_section(), multivariate_others(),
             "<h3 style='color:#16325c'>Diagnostics, reliability and planning</h3>", diagnostics(),
             "<h3 style='color:#16325c'>Signals and spectra</h3>", signal_section(), spectro_section(),
             "<h3 style='color:#16325c'>Geochemical calculations</h3>", geo_section()]
    return css + "<h2 id='methods'>13b. Methods guide: equations, when to use each tool, and how to read the results</h2>" + intro + "".join(parts)


if __name__ == "__main__":
    print(len(chapter()))
