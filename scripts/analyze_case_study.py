"""Generate analytical evidence and recommendations from configured input."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sql.data_engine import DataEngine,ROOT
from services.case_study import CaseStudy

def main():
    with DataEngine() as e:
        study=CaseStudy(e);adjusted=study.standardized_gap()
        frames={name:study.observations(group) for name,group in [('traffic','traffic_medium'),('month','session_month'),('latency','latency_band')]}
        for name,frame in frames.items():frame.to_csv(ROOT/'docs'/f'case-study-{name}.csv',index=False)
        (ROOT/'docs/case-study-adjusted.json').write_text(json.dumps(adjusted,indent=2)+'\n')
        total=frames['traffic'].groupby('device_category')[['users','checkouts']].sum()
        rows=['| Device | Eligible unique users | Checkout users | Conversion |','|---|---:|---:|---:|']
        for device,row in total.iterrows():rows.append(f'| {device} | {int(row.users):,} | {int(row.checkouts):,} | {row.checkouts/row.users:.2%} |')
        gap='Insufficient common-stratum observations.' if adjusted['gap'] is None else f"Traffic-standardized mobile minus desktop gap: **{adjusted['gap']*100:.2f} percentage points**, approximate 95% interval **[{adjusted['ci_lower']*100:.2f}, {adjusted['ci_upper']*100:.2f}]**. {adjusted['eligible_users']:,} users across {adjusted['common_strata']} common traffic strata contribute."
        body='''# Checkout progression: segment sensitivity case study

## Decision and measurement

Question: does the observed device gap persist after holding traffic-medium mix constant, and what evidence would justify a checkout experiment?

The bundled data is synthetic. These findings describe generation assumptions and demonstrate an analytical method; they are not customer research findings or realized business impact. Rerun against a consented real export before making a product decision.

Unit: each user's first observed cart session. Outcome: an ordered checkout within that session. Users without a cart session are outside this estimand. Device and medium come from that session. Repeated sessions are not treated as independent users.

## Observed conversion

'''+ '\n'.join(rows)+'\n\n## Composition sensitivity\n\n'+gap+'''

Weights represent the pooled medium mix across common strata with at least 30 users/device. The normal interval conditions on fixed weights. Excluded small/nonoverlapping strata limit generalization. Adjusted and unadjusted estimates use different population weights.

## Alternative explanations

- **Traffic composition:** inspect case-study-traffic.csv and the adjusted result. Disappearance of the gap after standardization would support acquisition mix as an explanation.
- **Calendar effects:** case-study-month.csv uses first eligible cart-session month, not true acquisition. Inspect stability across observed months.
- **Recorded load time:** case-study-latency.csv uses broad bands of session-average event load time, not checkout-specific latency or Core Web Vitals. Network, intent and device can confound this relationship.
- **Measurement loss:** blocked instrumentation, missing identifiers, late events, cross-device users and truncated sessions may bias denominators. Quality checks cannot detect all of these.
- **Revenue:** event revenue can contain duplicates. Use the separate accepted-transaction ledger for revenue reconciliation and keep currencies separate; do not extrapolate checkout conversion directly into annual revenue.

## Recommendation and falsification

Validate source completeness on real traffic and instrument step-level form errors and checkout-specific latency. If the gap persists within comparable sources and months, randomize eligible users to checkout simplification. Prespecify the MDE and fixed horizon; protect purchase conversion, net revenue per assigned user and payment errors. Check allocation ratios before inference.

Evidence that weakens the recommendation includes disappearance after traffic/calendar adjustment, differential event loss, insufficient overlap, or a randomized result excluding a practically important lift. The synthetic gap does not establish causality.

## Reproduce

Run `python scripts/analyze_case_study.py`. Supporting CSVs and adjusted JSON are generated from SQL; numerical conclusions are computed from the configured dataset.
'''
        (ROOT/'docs/CASE_STUDY.md').write_text(body);print(gap)
if __name__=='__main__':main()
