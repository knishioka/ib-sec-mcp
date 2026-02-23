# ETF計算ツール使用ガイド

**作成日**: 2025年10月17日
**対象**: Claude Desktop、Claude Code、開発者

---

## 📋 概要

ETF差し替え計算を**100%正確**に実行するためのMCPツール群。
すべての算術計算をPython側で実行し、LLMの計算ミスを完全に防止。

---

## 🛠️ 利用可能なツール

### 1. `calculate_etf_swap`

単一ETFの差し替え計算

**用途**:

- 「VOOをCSPXに差し替える場合、何株必要？」
- 「TLTからIDTLへの差し替えコストは？」
- 「年間メリットと投資回収期間は？」

**引数**:

```python
calculate_etf_swap(
    from_symbol="VOO",           # 売却するETF
    from_shares=40,              # 売却株数
    from_price=607.39,           # 売却価格
    from_expense_ratio=0.0003,   # 経費率（0.03%）
    from_dividend_yield=0.0115,  # 配当利回り（1.15%）
    from_withholding_tax=0.30,   # 源泉税率（30%）
    to_symbol="CSPX",            # 購入するETF
    to_price=714.78,             # 購入価格
    to_expense_ratio=0.0007,     # 経費率（0.07%）
    to_dividend_yield=0.0115,    # 配当利回り（1.15%）
    to_withholding_tax=0.00,     # 源泉税率（0%）
    trading_fee_usd=75.0         # 取引コスト（オプション）
)
```

**出力例**:

```json
{
  "from_etf": {
    "symbol": "VOO",
    "shares": 40,
    "price": 607.39,
    "total_value": 24295.6
  },
  "to_etf": {
    "symbol": "CSPX",
    "shares": 34,
    "price": 714.78,
    "total_value": 24302.52
  },
  "required_shares": 34,
  "purchase_amount": 24302.52,
  "surplus_cash": -6.92,
  "annual_withholding_tax_savings": 84.0,
  "annual_expense_change": -9.72,
  "annual_net_benefit": 74.28,
  "payback_period_months": 12.1
}
```

---

### 2. `calculate_portfolio_swap`

ポートフォリオ全体の差し替え計算

**用途**:

- 「複数のETFを一括で差し替える場合の総コストは？」
- 「ポートフォリオ全体での年間メリットは？」
- 「総投資回収期間は？」

**引数**:

```python
swaps_json = json.dumps([
    {
        "from_symbol": "VOO",
        "from_shares": 40,
        "from_price": 607.39,
        "from_expense_ratio": 0.0003,
        "from_dividend_yield": 0.0115,
        "from_withholding_tax": 0.30,
        "to_symbol": "CSPX",
        "to_price": 714.78,
        "to_expense_ratio": 0.0007,
        "to_dividend_yield": 0.0115,
        "to_withholding_tax": 0.00
    },
    {
        "from_symbol": "TLT",
        "from_shares": 200,
        "from_price": 91.34,
        "from_expense_ratio": 0.0015,
        "from_dividend_yield": 0.0433,
        "from_withholding_tax": 0.30,
        "to_symbol": "IDTL",
        "to_price": 3.40,
        "to_expense_ratio": 0.0007,
        "to_dividend_yield": 0.0445,
        "to_withholding_tax": 0.15
    }
])

calculate_portfolio_swap(
    swaps=swaps_json,
    trading_fee_usd=75.0
)
```

**出力例**:

```json
{
  "individual_results": [
    { "from_etf": {...}, "to_etf": {...}, ... },
    { "from_etf": {...}, "to_etf": {...}, ... }
  ],
  "summary": {
    "total_from_value": 42563.60,
    "total_to_value": 42570.72,
    "total_from_shares": 240,
    "total_to_shares": 5407,
    "surplus_cash": -7.12,
    "annual_withholding_savings": 199.18,
    "annual_expense_change": -4.89,
    "annual_net_benefit": 204.07,
    "payback_period_months": 4.4,
    "trading_fee": 75.0
  }
}
```

---

### 3. `validate_etf_price_mcp`

ETF価格の妥当性検証

**用途**:

- 「この価格は正しい？異常に低くない？」
- 「参照ETFと比較して妥当？」
- 「計算前に価格をチェックしたい」

**引数**:

```python
validate_etf_price_mcp(
    symbol="IDTL",
    price=3.40,
    reference_symbol="TLT",  # オプション
    reference_price=91.34    # オプション
)
```

**出力例**:

```json
{
  "symbol": "IDTL",
  "price": 3.4,
  "reference_symbol": "TLT",
  "reference_price": 91.34,
  "price_ratio": 0.037,
  "warnings": ["ℹ️ IDTLはTLTの3.7%の価格 - 1株あたりの設計が異なる（正常）"],
  "is_valid": true
}
```

---

## 📖 使用例

### ケース1: 単一ETFの差し替え

**ユーザー**:

```
TLT 200株をIDTLに差し替える場合、何株必要で年間メリットはいくら？
```

**Claude Desktopの処理**:

```python
# Step 1: 価格取得（WebSearch または get_current_price）
tlt_price = 91.34
idtl_price = 3.40

# Step 2: 価格検証
validation = validate_etf_price_mcp(
    symbol="IDTL",
    price=3.40,
    reference_symbol="TLT",
    reference_price=91.34
)
# 検証OK

# Step 3: 計算実行
result = calculate_etf_swap(
    from_symbol="TLT",
    from_shares=200,
    from_price=91.34,
    from_expense_ratio=0.0015,
    from_dividend_yield=0.0433,
    from_withholding_tax=0.30,
    to_symbol="IDTL",
    to_price=3.40,
    to_expense_ratio=0.0007,
    to_dividend_yield=0.0445,
    to_withholding_tax=0.15
)
```

**回答**:

```
TLT 200株をIDTLに差し替える場合：

必要株数: 5,373株
購入金額: $18,268.20
余剰金: -$0.20（ほぼ完全一致）

年間メリット:
- 配当源泉税削減: $115.36/年
- 経費削減: $14.61/年
- 純メリット: $129.98/年

投資回収期間: 約7ヶ月

注意: IDTLはTLTの1/27の価格設計です（正常）
```

---

### ケース2: ポートフォリオ全体の差し替え

**ユーザー**:

```
VOO、QQQ、TLT、INDA、VNMをすべてアイルランド籍ETFに差し替えた場合の
総コストと年間メリットを教えて。
```

**Claude Desktopの処理**:

```python
# 各ETFの価格を取得
# ... (省略) ...

# ポートフォリオ全体を計算
swaps = [
    {"from_symbol": "VOO", "to_symbol": "CSPX", ...},
    {"from_symbol": "QQQ", "to_symbol": "EQQQ", ...},
    {"from_symbol": "TLT", "to_symbol": "IDTL", ...},
    {"from_symbol": "INDA", "to_symbol": "SUIN", ...},
    {"from_symbol": "VNM", "to_symbol": "EIMI", ...},
]

result = calculate_portfolio_swap(
    swaps=json.dumps(swaps),
    trading_fee_usd=75.0
)
```

**回答**:

```
ポートフォリオ全体の差し替えサマリー:

総売却額: $75,806.00
総購入額: $75,860.00
必要な追加資金: $54.00

売却株数: 380株
購入株数: 5,643株

年間メリット:
- 配当源泉税削減: $312.50/年
- 経費増加: -$18.20/年
- 純メリット: $294.30/年

投資回収期間: 約3ヶ月
取引コスト$75を考慮しても3ヶ月で回収可能

推奨: すべて差し替えを推奨（年間$294の純メリット）
```

---

## 🔧 開発者向け: Pythonでの直接使用

```python
from decimal import Decimal
from ib_sec_mcp.tools.etf_calculator import ETFSwapCalculator

# 計算機の初期化
calculator = ETFSwapCalculator(trading_fee_usd=Decimal("75.00"))

# 単一ETFの計算
result = calculator.calculate_swap(
    from_symbol="VOO",
    from_shares=40,
    from_price=Decimal("607.39"),
    from_expense_ratio=Decimal("0.0003"),
    from_dividend_yield=Decimal("0.0115"),
    from_withholding_tax=Decimal("0.30"),
    to_symbol="CSPX",
    to_price=Decimal("714.78"),
    to_expense_ratio=Decimal("0.0007"),
    to_dividend_yield=Decimal("0.0115"),
    to_withholding_tax=Decimal("0.00"),
)

# 結果の表示
print(calculator.format_calculation_result(result))

# 結果へのアクセス
print(f"必要株数: {result.required_shares}")
print(f"年間メリット: ${result.annual_net_benefit:.2f}")
print(f"投資回収期間: {result.payback_period_months:.1f}ヶ月")
```

---

## ⚠️ 重要な注意事項

### 1. 価格の正確性

MCPツールは入力された価格を信頼します。
**必ず最新の正確な価格を使用してください。**

推奨:

- `get_current_price()` MCPツールで取得
- Yahoo Finance等の信頼できるソースから取得
- 計算前に`validate_etf_price_mcp()`で検証

### 2. 計算の前提

- **取引コスト**: デフォルト$75（変更可能）
- **端数処理**: ROUND_HALF_UP（四捨五入）
- **通貨**: すべてUSD建て
- **配当**: 年間ベース
- **経費率**: 年間ベース

### 3. LLMは計算しない

**重要**: LLMは以下を行わない:

- ❌ 算術計算（足し算、掛け算、割り算）
- ❌ 株数の計算
- ❌ 年間メリットの計算
- ❌ 投資回収期間の計算

すべての計算はPython側で実行され、LLMは結果を整形するのみ。

### 4. 検証の重要性

計算前に必ず`validate_etf_price_mcp()`を使用:

```python
# 悪い例（検証なし）
result = calculate_etf_swap(...)  # 誤った価格でも計算

# 良い例（検証あり）
validation = validate_etf_price_mcp(...)
if validation["is_valid"]:
    result = calculate_etf_swap(...)
else:
    print("警告:", validation["warnings"])
    # 人間に確認を求める
```

---

## 🎯 よくある質問

### Q1: なぜPython側で計算するのか？

**A**: LLMは算術計算が苦手で、誤りが発生しやすいため。

**実例**: 今回のIDTL価格計算

- LLM計算: $88.67（26倍の誤り）
- Python計算: $3.40（正確）

### Q2: なぜDecimal型を使うのか？

**A**: float型は浮動小数点誤差があり、金融計算には不適切。

```python
# float型（誤差あり）
0.1 + 0.2 == 0.3  # False!

# Decimal型（正確）
Decimal("0.1") + Decimal("0.2") == Decimal("0.3")  # True
```

### Q3: 価格が異常に低い場合は？

**A**: `validate_etf_price_mcp()`が警告を出します。

例: IDTL $3.40（TLTの1/27）

```json
{
  "is_valid": true,
  "warnings": ["ℹ️ IDTLはTLTの3.7%の価格 - 1株あたりの設計が異なる（正常）"]
}
```

**注意**: 警告が出ても`is_valid: true`の場合、価格は正常です。
参照ETFと設計が異なるだけです。

### Q4: 複数アカウントの計算は？

**A**: `calculate_portfolio_swap()`を使用してすべてのETFをまとめて計算。

各アカウントのETFを1つのリストにまとめれば、複数アカウントにも対応。

---

## 📚 関連ドキュメント

- **`docs/calculation_error_prevention_strategy.md`** - 対策戦略全体
- **`ib_sec_mcp/tools/etf_calculator.py`** - 実装コード

---

**作成者**: IB Analytics Development Team
**最終更新**: 2025年10月17日
**バージョン**: 1.0.0
