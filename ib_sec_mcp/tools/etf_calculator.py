"""
ETF差し替え計算ツール

アイルランド籍ETFへの組み替え時の必要株数を正確に計算する。
LLMによる算術計算ミスを防ぐため、すべての計算をPython側で実施。
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass
class ETFPosition:
    """ETFポジション情報"""

    symbol: str
    shares: Decimal
    price: Decimal
    total_value: Decimal
    expense_ratio: Decimal
    dividend_yield: Decimal
    withholding_tax_rate: Decimal  # 源泉税率（例：0.30 = 30%）


@dataclass
class SwapCalculation:
    """差し替え計算結果"""

    from_etf: ETFPosition
    to_etf: ETFPosition
    required_shares: int  # 購入必要株数
    purchase_amount: Decimal
    surplus_cash: Decimal
    annual_withholding_tax_savings: Decimal
    annual_expense_change: Decimal
    annual_net_benefit: Decimal
    payback_period_months: float  # 投資回収期間（月）


class ETFSwapCalculator:
    """ETF差し替え計算機"""

    def __init__(self, trading_fee_usd: Decimal = Decimal("75.00")):
        """
        Args:
            trading_fee_usd: 取引コスト（デフォルト$75）
        """
        self.trading_fee = trading_fee_usd

    def calculate_swap(
        self,
        from_symbol: str,
        from_shares: int,
        from_price: Decimal,
        from_expense_ratio: Decimal,
        from_dividend_yield: Decimal,
        from_withholding_tax: Decimal,
        to_symbol: str,
        to_price: Decimal,
        to_expense_ratio: Decimal,
        to_dividend_yield: Decimal,
        to_withholding_tax: Decimal,
    ) -> SwapCalculation:
        """
        ETF差し替えの計算を実行

        Args:
            from_symbol: 売却するETFのシンボル
            from_shares: 売却株数
            from_price: 売却価格
            from_expense_ratio: 経費率（例：0.0003 = 0.03%）
            from_dividend_yield: 配当利回り（例：0.0115 = 1.15%）
            from_withholding_tax: 源泉税率（例：0.30 = 30%）
            to_symbol: 購入するETFのシンボル
            to_price: 購入価格
            to_expense_ratio: 経費率
            to_dividend_yield: 配当利回り
            to_withholding_tax: 源泉税率

        Returns:
            SwapCalculation: 計算結果
        """
        # 売却額の計算
        from_total = Decimal(from_shares) * from_price

        # 購入可能株数の計算（端数切り上げ）
        required_shares_decimal = from_total / to_price
        required_shares = int(
            required_shares_decimal.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )

        # 実際の購入金額
        purchase_amount = Decimal(required_shares) * to_price

        # 余剰金または不足金
        surplus_cash = from_total - purchase_amount

        # 年間配当額
        from_annual_dividend = from_total * from_dividend_yield
        to_annual_dividend = purchase_amount * to_dividend_yield

        # 年間源泉税
        from_annual_withholding = from_annual_dividend * from_withholding_tax
        to_annual_withholding = to_annual_dividend * to_withholding_tax

        # 年間源泉税削減額
        annual_withholding_savings = from_annual_withholding - to_annual_withholding

        # 年間経費
        from_annual_expense = from_total * from_expense_ratio
        to_annual_expense = purchase_amount * to_expense_ratio

        # 年間経費変化（マイナスなら削減、プラスなら増加）
        annual_expense_change = to_annual_expense - from_annual_expense

        # 年間純メリット
        annual_net_benefit = annual_withholding_savings - annual_expense_change

        # 投資回収期間（月）
        if annual_net_benefit > 0:
            payback_period_months = float((self.trading_fee / annual_net_benefit) * Decimal("12"))
        else:
            payback_period_months = float("inf")

        # ETFポジション作成
        from_etf = ETFPosition(
            symbol=from_symbol,
            shares=Decimal(from_shares),
            price=from_price,
            total_value=from_total,
            expense_ratio=from_expense_ratio,
            dividend_yield=from_dividend_yield,
            withholding_tax_rate=from_withholding_tax,
        )

        to_etf = ETFPosition(
            symbol=to_symbol,
            shares=Decimal(required_shares),
            price=to_price,
            total_value=purchase_amount,
            expense_ratio=to_expense_ratio,
            dividend_yield=to_dividend_yield,
            withholding_tax_rate=to_withholding_tax,
        )

        return SwapCalculation(
            from_etf=from_etf,
            to_etf=to_etf,
            required_shares=required_shares,
            purchase_amount=purchase_amount,
            surplus_cash=surplus_cash,
            annual_withholding_tax_savings=annual_withholding_savings,
            annual_expense_change=annual_expense_change,
            annual_net_benefit=annual_net_benefit,
            payback_period_months=payback_period_months,
        )

    def format_calculation_result(self, calc: SwapCalculation) -> str:
        """
        計算結果を人間が読みやすい形式でフォーマット

        Args:
            calc: 計算結果

        Returns:
            フォーマットされた文字列
        """
        lines = [
            "=== ETF差し替え計算結果 ===",
            "",
            "【売却】",
            f"  {calc.from_etf.symbol}: {calc.from_etf.shares:,.0f}株 × ${calc.from_etf.price:,.2f} = ${calc.from_etf.total_value:,.2f}",
            f"  経費率: {calc.from_etf.expense_ratio * 100:.2f}%",
            f"  配当利回り: {calc.from_etf.dividend_yield * 100:.2f}%",
            f"  源泉税率: {calc.from_etf.withholding_tax_rate * 100:.0f}%",
            "",
            "【購入】",
            f"  {calc.to_etf.symbol}: {calc.required_shares:,}株 × ${calc.to_etf.price:,.2f} = ${calc.purchase_amount:,.2f}",
            f"  経費率: {calc.to_etf.expense_ratio * 100:.2f}%",
            f"  配当利回り: {calc.to_etf.dividend_yield * 100:.2f}%",
            f"  源泉税率: {calc.to_etf.withholding_tax_rate * 100:.0f}%",
            "",
            "【差額】",
            f"  余剰金/不足金: ${calc.surplus_cash:+,.2f}",
            "",
            "【年間メリット】",
            f"  源泉税削減: ${calc.annual_withholding_tax_savings:,.2f}/年",
            f"  経費変化: ${calc.annual_expense_change:+,.2f}/年",
            f"  純メリット: ${calc.annual_net_benefit:,.2f}/年",
            "",
            "【投資回収期間】",
        ]

        if calc.payback_period_months == float("inf"):
            lines.append("  メリットなし（経費増加が源泉税削減を上回る）")
        else:
            lines.append(
                f"  {calc.payback_period_months:.1f}ヶ月（約{calc.payback_period_months / 12:.1f}年）"
            )

        return "\n".join(lines)

    def calculate_portfolio_swap(self, swaps: list[dict]) -> dict:
        """
        ポートフォリオ全体の差し替え計算

        Args:
            swaps: 差し替えリスト
                [
                    {
                        "from_symbol": "VOO",
                        "from_shares": 40,
                        "from_price": 607.39,
                        ...
                    },
                    ...
                ]

        Returns:
            集計結果の辞書
        """
        results = []
        total_from_value = Decimal("0")
        total_to_value = Decimal("0")
        total_from_shares = 0
        total_to_shares = 0
        total_annual_savings = Decimal("0")
        total_expense_change = Decimal("0")

        for swap_data in swaps:
            calc = self.calculate_swap(
                from_symbol=swap_data["from_symbol"],
                from_shares=swap_data["from_shares"],
                from_price=Decimal(str(swap_data["from_price"])),
                from_expense_ratio=Decimal(str(swap_data["from_expense_ratio"])),
                from_dividend_yield=Decimal(str(swap_data["from_dividend_yield"])),
                from_withholding_tax=Decimal(str(swap_data["from_withholding_tax"])),
                to_symbol=swap_data["to_symbol"],
                to_price=Decimal(str(swap_data["to_price"])),
                to_expense_ratio=Decimal(str(swap_data["to_expense_ratio"])),
                to_dividend_yield=Decimal(str(swap_data["to_dividend_yield"])),
                to_withholding_tax=Decimal(str(swap_data["to_withholding_tax"])),
            )

            results.append(calc)
            total_from_value += calc.from_etf.total_value
            total_to_value += calc.purchase_amount
            total_from_shares += int(calc.from_etf.shares)
            total_to_shares += calc.required_shares
            total_annual_savings += calc.annual_withholding_tax_savings
            total_expense_change += calc.annual_expense_change

        total_net_benefit = total_annual_savings - total_expense_change

        if total_net_benefit > 0:
            total_payback_months = float((self.trading_fee / total_net_benefit) * Decimal("12"))
        else:
            total_payback_months = float("inf")

        return {
            "individual_results": results,
            "summary": {
                "total_from_value": float(total_from_value),
                "total_to_value": float(total_to_value),
                "total_from_shares": total_from_shares,
                "total_to_shares": total_to_shares,
                "surplus_cash": float(total_from_value - total_to_value),
                "annual_withholding_savings": float(total_annual_savings),
                "annual_expense_change": float(total_expense_change),
                "annual_net_benefit": float(total_net_benefit),
                "payback_period_months": total_payback_months,
                "trading_fee": float(self.trading_fee),
            },
        }


def validate_etf_price(
    symbol: str,
    price: Decimal,
    reference_symbol: str | None = None,
    reference_price: Decimal | None = None,
) -> dict[str, any]:
    """
    ETF価格の妥当性を検証

    Args:
        symbol: ETFシンボル
        price: 価格
        reference_symbol: 参照ETFシンボル（同じ指数を追跡）
        reference_price: 参照ETF価格

    Returns:
        検証結果
    """
    warnings = []

    # 価格が異常に低い/高いかチェック
    if price < Decimal("1.00"):
        warnings.append(f"⚠️ {symbol}の価格${price:.2f}は非常に低い（$1未満）- 低価格ETFの可能性")

    if price > Decimal("1000.00"):
        warnings.append(f"⚠️ {symbol}の価格${price:.2f}は非常に高い（$1,000超）")

    # 参照ETFとの比較
    price_ratio = None
    if reference_symbol and reference_price:
        price_ratio = float(price / reference_price)

        if price_ratio < 0.01:
            warnings.append(
                f"⚠️ {symbol}は{reference_symbol}の{price_ratio * 100:.1f}%の価格 "
                f"- 低価格ETFの可能性（正常な場合もあり）"
            )
        elif price_ratio > 100:
            warnings.append(
                f"⚠️ {symbol}は{reference_symbol}の{price_ratio:.0f}倍の価格 "
                f"- 価格情報が誤っている可能性"
            )
        elif price_ratio < 0.5 or price_ratio > 2.0:
            warnings.append(
                f"ℹ️ {symbol}は{reference_symbol}の{price_ratio:.2f}倍の価格 "
                f"- 1株あたりの設計が異なる（正常）"
            )

    return {
        "symbol": symbol,
        "price": float(price),
        "reference_symbol": reference_symbol,
        "reference_price": float(reference_price) if reference_price else None,
        "price_ratio": price_ratio,
        "warnings": warnings,
        "is_valid": len([w for w in warnings if w.startswith("⚠️")]) == 0,
    }
