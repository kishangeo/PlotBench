# IsoplotR side of the cross-check: York regression of the IsoplotR Rb-Sr example and the concordia age of the IsoplotR U-Pb example
# (Wetherill space, decay-constant errors excluded). Writes isoplotr.json. Run: Rscript validation/crosscheck/isoplotr_side.R
# Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
library(IsoplotR)
f <- grep("--file=", commandArgs(FALSE), value = TRUE); here <- if (length(f)) dirname(sub("--file=", "", f)) else "."
rb <- IsoplotR:::data2york(examples$RbSr)                       # X = 87Rb/86Sr, Y = 87Sr/86Sr, 1-sigma, rXY
yf <- york(rb)
up <- IsoplotR:::data2york(examples$UPb, option = 1)           # Wetherill: X = 207Pb/235U, Y = 206Pb/238U
ca <- IsoplotR:::concordia_age(examples$UPb, type = 1, exterr = FALSE)
num <- function(v) paste0("[", paste(sprintf("%.17g", v), collapse = ","), "]")
tab <- function(m) paste0("{", paste(sprintf('"%s":%s', c("x", "sx", "y", "sy", "rho"), sapply(1:5, function(i) num(m[, i]))), collapse = ","), "}")
cat(sprintf('{"version":"%s","rbsr":%s,"york":{"slope":%.17g,"s_slope":%.17g,"intercept":%.17g,"s_intercept":%.17g,"mswd":%.17g},"upb":%s,"concordia":{"age":%.17g,"s_age":%.17g,"mswd_conc":%.17g}}',
            as.character(packageVersion("IsoplotR")), tab(rb), yf$b[1], yf$b[2], yf$a[1], yf$a[2], yf$mswd, tab(up),
            ca$age[1], ca$age[2], ca$mswd["concordance"]), file = file.path(here, "isoplotr.json"))
print(yf[c("a", "b", "mswd")]); print(ca$age); print(ca$mswd)
