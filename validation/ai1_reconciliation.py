"""Validation harness — A.CRE Ai1 reconciliation.

Deal spec per Ai1 mapper research (2026-05-29):
    50,000 sf single-tenant office, pure NNN, 5-year hold,
    $15M acquisition, 60% LTV ($9M) at 5.5% / 30-yr amort,
    7.0% exit cap, 2.5% sale costs.

Lease: 50,000 sf, $30/sf base NNN, 3% annual bumps, 100% recovery,
7-year term (no rollover during hold).

OpEx: CAM $3.00/sf + RE Tax $4.00/sf + Insurance $0.50/sf
    = $7.50/sf year 1 ($375k), 3% annual growth.

Management fee (3% of EGI in Ai1 spec) dropped — OpenVal does not
yet support % of EGI line items. Phase 2.
"""

from datetime import date
from decimal import Decimal

from openval import ExpenseStructure, Lease, Loan, Property, RentStep, project_property


def build_deal() -> Property:
    base_psf = Decimal("30.00")
    rent_steps = [
        RentStep(
            start_date=date(2026 + i, 1, 1),
            annual_psf=(base_psf * (Decimal("1.03") ** i)).quantize(Decimal("0.0001")),
        )
        for i in range(7)
    ]

    lease = Lease(
        suite_id="100",
        tenant_name="Tenant A",
        area_sf=50_000,
        start_date=date(2026, 1, 1),
        end_date=date(2033, 1, 1),
        base_rent_steps=rent_steps,
        expense_structure=ExpenseStructure.NNN,
    )

    base_opex = Decimal("375000")
    opex_annual = {
        2026 + i: (base_opex * (Decimal("1.03") ** i)).quantize(Decimal("0.01"))
        for i in range(5)
    }

    loan = Loan(
        principal=Decimal("9000000"),
        rate_annual=Decimal("0.055"),
        amortization_years=30,
        term_years=10,
    )

    return Property(
        name="Validation Office",
        rentable_sf=50_000,
        leases=[lease],
        opex_annual=opex_annual,
        acquisition_date=date(2026, 1, 1),
        acquisition_price=Decimal("15000000"),
        hold_years=5,
        exit_cap_rate=Decimal("0.07"),
        sale_costs_pct=Decimal("0.025"),
        loan=loan,
    )


def print_report(prop: Property, result) -> None:
    cf = result.cashflows

    print("=" * 72)
    print("OPENVAL VALIDATION DEAL — Ai1 reconciliation")
    print("=" * 72)
    print()
    print(f"  Property:           {prop.name}")
    print(f"  Acquisition price:  ${float(prop.acquisition_price):>16,.0f}")
    print(f"  Loan principal:     ${float(prop.loan.principal):>16,.0f}")
    print(f"  Equity (levered):   ${float(prop.acquisition_price - prop.loan.principal):>16,.0f}")
    print(f"  Hold:               {prop.hold_years} years")
    print(f"  Exit cap rate:      {float(prop.exit_cap_rate):>16.2%}")
    print(f"  Sale costs:         {float(prop.sale_costs_pct):>16.2%}")
    print()

    print("ANNUAL ROLLUP")
    print("-" * 72)
    print(f"{'Year':>6} {'Gross Rent':>14} {'Recovery':>14} {'OpEx':>14} {'NOI':>14}")
    for year_i in range(prop.hold_years):
        year = prop.acquisition_date.year + year_i
        ydata = cf[cf.index.year == year]
        gross = ydata["gross_rent"].sum()
        rec = ydata["recoveries"].sum()
        opex = ydata["opex"].sum()
        noi = ydata["noi"].sum()
        print(f"{year:>6} {gross:>14,.0f} {rec:>14,.0f} {opex:>14,.0f} {noi:>14,.0f}")
    print()

    print("REVERSION (trailing-12 NOI / cap)")
    print("-" * 72)
    print(f"  Terminal NOI (year-5 trailing):  ${result.reversion.terminal_noi:>16,.0f}")
    print(f"  Gross sale price:                ${result.reversion.gross_sale_price:>16,.0f}")
    print(f"  Sale costs:                      ${result.reversion.sale_costs:>16,.0f}")
    print(f"  Net sale:                        ${result.reversion.net_sale:>16,.0f}")
    print(f"  Loan payoff at sale:             ${result.reversion.loan_payoff:>16,.0f}")
    print(f"  Net sale to equity:              ${result.reversion.net_sale_to_equity:>16,.0f}")
    print()

    print("RETURNS")
    print("-" * 72)
    print(f"  Unlevered IRR:                   {result.unlevered_irr:>16.4%}")
    print(f"  Levered IRR:                     {result.levered_irr:>16.4%}")
    print(f"  Unlevered equity multiple:       {result.unlevered_equity_multiple:>16.3f}x")
    print(f"  Levered equity multiple:         {result.levered_equity_multiple:>16.3f}x")
    print()

    print("EXPECTED Ai1 DELTAS")
    print("-" * 72)
    print("  • Ai1 uses FORWARD NOI (year-6) for reversion, not trailing-12.")
    print("    Expect Ai1 gross sale ≈ our value × 1.03 (one extra year of growth).")
    print("    Expect Ai1 IRRs slightly higher because of larger exit value.")
    print("  • Management fee dropped on both sides for comparison")
    print("    (OpenVal doesn't yet support % of EGI line items).")
    print("  • 100% NNN recoveries — Ai1's NNN treatment is clean.")
    print("    (MG/Base-Year in Ai1 are documented approximations; avoided here.)")


if __name__ == "__main__":
    prop = build_deal()
    result = project_property(prop)
    print_report(prop, result)
