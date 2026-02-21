"""
Cross-campaign strategic validator.

Checks coherence and differentiation ACROSS campaign types after all generators
have run. Catches issues that individual agents cannot see in isolation:
- Copy overlap between Brand and Acquisition
- Budget coherence across the full campaign mix
- Demand Gen minimum budget threshold
"""
from __future__ import annotations

from typing import List

from app.domain.schemas.brief import Brief


class StrategicValidator:
    """
    Runs AFTER individual agent validators to check cross-campaign consistency.
    These are the checks described in "CONTROLLO STRATEGICO FINALE OBBLIGATORIO".
    """

    def validate(self, brief: Brief) -> List[str]:
        warnings: List[str] = []
        warnings.extend(self._check_copy_differentiation(brief))
        warnings.extend(self._check_budget_mix(brief))
        warnings.extend(self._check_search_vs_pmax_differentiation(brief))
        return warnings

    # ── Copy differentiation ───────────────────────────────────────────────────

    def _check_copy_differentiation(self, brief: Brief) -> List[str]:
        """
        Warn when Brand and Acquisition share too many identical headlines.
        Only triggers when both have specific per-type assets configured
        (individual agents already warn when specific assets are missing).
        """
        warnings: List[str] = []

        for lang in brief.languages:
            has_brand = bool(lang.brand_assets and lang.brand_assets.headlines)
            has_acq = bool(lang.acquisition_assets and lang.acquisition_assets.headlines)

            if not (has_brand and has_acq):
                continue

            brand_set = {h.strip().lower() for h in lang.brand_assets.headlines}
            acq_set = {h.strip().lower() for h in lang.acquisition_assets.headlines}
            overlap = brand_set & acq_set

            if overlap:
                pct = len(overlap) / min(len(brand_set), len(acq_set))
                if pct >= 0.25:
                    examples = '", "'.join(list(overlap)[:2])
                    warnings.append(
                        f"[Strategia/{lang.code}] {len(overlap)} headline identici tra Brand e Acquisition "
                        f'(es. "{examples}"). '
                        "Brand copy = prenotazione diretta/sito ufficiale; "
                        "Acquisition copy = categoria/destinazione/USP senza brand name. "
                        "Due campagne con copy simile segnalano un errore strategico — rigenera."
                    )

            # Warn if retargeting copy looks identical to acquisition
            has_ret = bool(lang.retargeting_assets and lang.retargeting_assets.headlines)
            if has_ret and has_acq:
                ret_set = {h.strip().lower() for h in lang.retargeting_assets.headlines}
                overlap_ret = ret_set & acq_set
                if overlap_ret:
                    pct_ret = len(overlap_ret) / min(len(ret_set), len(acq_set))
                    if pct_ret >= 0.25:
                        warnings.append(
                            f"[Strategia/{lang.code}] {len(overlap_ret)} headline identici tra Retargeting e Acquisition. "
                            "Retargeting = urgency/personalizzazione per utenti che già conoscono l'hotel. "
                            "Non deve usare la stessa copy della Acquisition prospecting."
                        )

        return warnings

    # ── Budget mix ─────────────────────────────────────────────────────────────

    def _check_budget_mix(self, brief: Brief) -> List[str]:
        """
        Verify the overall budget allocation is strategically coherent.
        A healthy hotel account has: Brand (5-15%) + Acquisition (30-45%) +
        PMax (30-50%) as core, with Retargeting and DemandGen as support.
        """
        warnings: List[str] = []
        total = brief.budgets.total_monthly_eur
        if total <= 0:
            return warnings

        active_types = {
            k: v for k, v in brief.budgets.by_campaign_type.items()
            if v and v.total > 0
        }

        # Check that Brand budget < Acquisition budget (brand is protect, not grow)
        brand_budget = (active_types.get("search_brand") or None)
        acq_budget = (active_types.get("search_acquisition") or None)
        if brand_budget and acq_budget:
            if brand_budget.total > acq_budget.total:
                brand_pct = brand_budget.total / total * 100
                acq_pct = acq_budget.total / total * 100
                warnings.append(
                    f"[Strategia] Budget Brand ({brand_pct:.1f}%) > Budget Acquisition ({acq_pct:.1f}%). "
                    "Brand campaign difende domanda esistente (piccolo volume, cheap). "
                    "Acquisition deve avere budget maggiore per crescita. "
                    "Redistribuisci: Brand 5–15%, Acquisition 30–45%."
                )

        # Check Demand Gen minimum
        dg = active_types.get("demand_gen")
        if dg:
            dg_pct = dg.total / total * 100
            if dg_pct < 5:
                warnings.append(
                    f"[Strategia] Demand Gen budget {dg_pct:.1f}% del totale (min 5%). "
                    "Sotto il 5% non si raggiunge massa critica per l'apprendimento algoritmico. "
                    "O porta Demand Gen ad almeno il 5% o disattivala temporaneamente."
                )

        return warnings

    # ── Search vs PMax differentiation ────────────────────────────────────────

    def _check_search_vs_pmax_differentiation(self, brief: Brief) -> List[str]:
        """
        PMax should NOT be a copy of the Search campaigns.
        They have different reach, format and optimization logic.
        """
        warnings: List[str] = []

        pmax_active = (
            brief.budgets.by_campaign_type.get("performance_max") is not None
            and brief.budgets.by_campaign_type["performance_max"].total > 0
        )
        brand_active = (
            brief.budgets.by_campaign_type.get("search_brand") is not None
            and brief.budgets.by_campaign_type["search_brand"].total > 0
        )

        if pmax_active and brand_active:
            # Check for missing brand exclusion indicator (no brand terms)
            no_brand_terms = all(not lang.brand_terms for lang in brief.languages)
            if no_brand_terms:
                warnings.append(
                    "[Strategia] PMax + Brand Search attivi ma nessun brand term configurato. "
                    "Senza brand terms non è possibile impostare brand exclusion in PMax: "
                    "PMax cannibalizzerà la Brand Search sulle query branded entro 2 settimane."
                )

        return warnings
