"""Statistics for independent user observations, not causal attribution."""
from math import sqrt, ceil
from scipy.stats import norm, chi2_contingency

def wilson_interval(k, n, z=1.95996398454):
    if n < 0 or k < 0 or k > n:
        raise ValueError('Require 0 <= k <= n')
    if n == 0:
        return None, None
    p=k/n
    center=(p+z*z/(2*n))/(1+z*z/n)
    half=z*sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return (0.0 if k == 0 else max(0,center-half)), (1.0 if k == n else min(1,center+half))

def compare_groups(table):
    if len(table)!=2 or any(len(row)!=2 or min(row)<0 or sum(row)==0 for row in table):
        return None
    if any(sum(row[j] for row in table)==0 for j in range(2)):
        return None
    chi,p,_,expected=chi2_contingency(table)
    if expected.min()<5:
        return None
    return {'chi_square':float(chi),'p_value':float(p)}

def sample_size(baseline, absolute_lift, alpha=.05, power=.8):
    target=baseline+absolute_lift
    if not 0<baseline<target<1 or not 0<alpha<1 or not 0<power<1:
        raise ValueError('Invalid planning assumptions')
    pooled=(baseline+target)/2
    return ceil(((norm.ppf(1-alpha/2)*sqrt(2*pooled*(1-pooled))+norm.ppf(power)*sqrt(baseline*(1-baseline)+target*(1-target)))/absolute_lift)**2)
