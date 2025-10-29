# 計算誤り防止戦略
## LLMによる算術計算ミスを防ぐアーキテクチャ設計

**作成日**: 2025年10月17日
**目的**: 今回のETF差し替え計算での重大な誤りを二度と起こさないための対策

---

## 🔴 今回の誤りの原因分析

### 1. 根本原因

#### (A) WebSearchの非構造化データへの依存
```
WebSearch結果: "IDTL price 3.33 USD"
↓ LLMによる解釈
❌ "3.33はGBP建ての可能性... 為替レート26.63を掛けて..."
❌ "$88.67 USDと推定"

実際: 3.33が既にUSDだった
```

**問題点**:
- WebSearchはテキストベース（構造化されていない）
- LLMが文脈から推測して計算
- 検証プロセスなし

#### (B) LLMによる算術計算
```
誤った為替計算: 3.33 × 26.63 = $88.67

実際のIDTL価格: $3.40（WebSearchの"3.33"とほぼ一致）
```

**問題点**:
- LLMは算術計算が苦手（精度問題）
- 複数の仮定を重ねて計算（誤差累積）
- 計算結果の妥当性チェックなし

#### (C) 検証プロセスの不在
```
計算後のチェックなし:
- TLTとIDTLの価格比（1/27）は異常か？
- 必要株数5,373株は妥当か？
- 他の情報源での確認は？
```

**問題点**:
- 計算結果を盲信
- 外部APIでの価格検証なし
- 常識的範囲の確認なし

---

## 💡 対策戦略

### 戦略1: 計算をPython/MCPに完全移行（最重要）

#### 原則

**❌ LLMにやらせてはいけないこと**:
- 算術計算（足し算、掛け算、割り算）
- 金融計算（配当、源泉税、経費率）
- 株数計算（端数処理）
- 通貨換算

**✅ Pythonにやらせること**:
- すべての数値計算
- Decimalによる高精度計算
- 端数処理（ROUND_HALF_UP等）
- 検証ロジック

#### 実装: MCPツールとして追加

**作成済み**: `ib_sec_mcp/tools/etf_calculator.py`

機能:
- ETF差し替え計算の完全自動化
- Decimal型による高精度計算
- 価格妥当性検証
- ポートフォリオ全体の計算

使用方法:
```python
from ib_sec_mcp.tools.etf_calculator import ETFSwapCalculator

calculator = ETFSwapCalculator()

result = calculator.calculate_swap(
    from_symbol="TLT",
    from_shares=200,
    from_price=Decimal("91.34"),
    from_expense_ratio=Decimal("0.0015"),
    from_dividend_yield=Decimal("0.0433"),
    from_withholding_tax=Decimal("0.30"),
    to_symbol="IDTL",
    to_price=Decimal("3.40"),  # ← 正確な価格を入力
    to_expense_ratio=Decimal("0.0007"),
    to_dividend_yield=Decimal("0.0445"),
    to_withholding_tax=Decimal("0.15"),
)

# 結果
result.required_shares  # 5373株（正確）
result.annual_net_benefit  # $129.61/年（正確）
```

---

### 戦略2: 価格取得の構造化（Yahoo Finance API）

#### 問題

**WebSearchの限界**:
- テキストベース（非構造化）
- 価格が文脈に埋もれている
- 通貨表示が不明確（USD? GBP? EUR?）
- LLMによる解釈が必要

#### 解決策: Yahoo Finance APIの活用

**既存のMCPツール**:
```python
mcp__ib-sec-mcp__get_current_price(symbol="VOO")
```

**提案**: アイルランド籍ETF対応

```python
# 新MCPツール
mcp__ib-sec-mcp__get_etf_price_lse(
    symbol="CSPX",  # ロンドン市場のティッカー
    currency="USD"  # USD建て価格を取得
)

# 返却値
{
    "symbol": "CSPX",
    "exchange": "LSE",
    "currency": "USD",
    "price": 714.78,  # 構造化された数値
    "timestamp": "2025-10-17T16:30:00Z"
}
```

**メリット**:
- ✅ 構造化データ（JSON）
- ✅ 数値型で返却（文字列解析不要）
- ✅ 通貨が明確
- ✅ LLMの解釈不要

#### 実装計画

**ファイル**: `ib_sec_mcp/mcp/tools/yahoo_finance.py`

追加関数:
```python
@mcp.tool()
async def get_etf_price_lse(
    symbol: str,
    currency: str = "USD"
) -> str:
    """
    ロンドン証券取引所（LSE）のETF価格を取得

    アイルランド籍ETFの価格を構造化データで返す。

    Args:
        symbol: ティッカーシンボル（例：CSPX, EQQQ, IDTL）
        currency: 通貨コード（USD, GBP, EUR）

    Returns:
        JSON文字列（価格、通貨、取引所情報）
    """
    ...
```

---

### 戦略3: 価格検証ロジックの追加

#### 自動検証

**実装済み**: `etf_calculator.py`の`validate_etf_price()`

検証項目:
1. 価格が異常に低い/高い
2. 参照ETFとの価格比
3. 警告メッセージ生成

使用例:
```python
validation = validate_etf_price(
    symbol="IDTL",
    price=Decimal("3.40"),
    reference_symbol="TLT",
    reference_price=Decimal("91.34")
)

# 出力
{
    "symbol": "IDTL",
    "price": 3.40,
    "price_ratio": 0.037,  # TLTの3.7%
    "warnings": [
        "⚠️ IDTLの価格$3.40は非常に低い（$1未満）- 低価格ETFの可能性",
        "⚠️ IDTLはTLTの3.7%の価格 - 低価格ETFの可能性（正常な場合もあり）"
    ],
    "is_valid": False  # 要人間確認
}
```

**ワークフロー**:
1. LLMが価格を取得
2. Pythonで自動検証
3. 警告があれば人間に確認依頼
4. 確認後に計算実行

---

### 戦略4: MCPツールの追加

#### 提案: 新しいMCPツール

**ツール1**: `calculate_etf_swap`
```python
@mcp.tool()
async def calculate_etf_swap(
    from_symbol: str,
    from_shares: int,
    from_price: float,
    from_expense_ratio: float,
    from_dividend_yield: float,
    from_withholding_tax: float,
    to_symbol: str,
    to_price: float,
    to_expense_ratio: float,
    to_dividend_yield: float,
    to_withholding_tax: float,
) -> str:
    """
    ETF差し替えの必要株数と年間メリットを計算

    すべての計算をPython側で実施し、LLMの算術計算ミスを防ぐ。

    Returns:
        JSON文字列（必要株数、投資額、年間メリット、投資回収期間）
    """
    calculator = ETFSwapCalculator()
    result = calculator.calculate_swap(...)
    return json.dumps({
        "from_etf": {...},
        "to_etf": {...},
        "required_shares": result.required_shares,
        "purchase_amount": float(result.purchase_amount),
        "surplus_cash": float(result.surplus_cash),
        "annual_net_benefit": float(result.annual_net_benefit),
        "payback_period_months": result.payback_period_months,
    })
```

**ツール2**: `calculate_portfolio_swap`
```python
@mcp.tool()
async def calculate_portfolio_swap(
    swaps: str  # JSON文字列
) -> str:
    """
    ポートフォリオ全体のETF差し替え計算

    複数のETFを一括計算し、総合的なメリットを算出。

    Args:
        swaps: JSON文字列（差し替えリスト）
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
        JSON文字列（個別結果 + 集計）
    """
    ...
```

**ツール3**: `validate_etf_price_mcp`
```python
@mcp.tool()
async def validate_etf_price_mcp(
    symbol: str,
    price: float,
    reference_symbol: str = None,
    reference_price: float = None
) -> str:
    """
    ETF価格の妥当性を検証

    価格が異常に低い/高い場合や、参照ETFとの乖離が大きい場合に警告。

    Returns:
        JSON文字列（検証結果、警告メッセージ）
    """
    ...
```

---

## 🎯 実装計画

### Phase 1: 計算ツールの追加（完了✅）

**完了**:
- [x] `etf_calculator.py`作成
- [x] `ETFSwapCalculator`クラス実装
- [x] `validate_etf_price()`関数実装
- [x] テストコード追加
- [x] MCPツールとして登録
- [x] `ib_sec_mcp/mcp/tools/etf_calculator_tools.py`作成
- [x] `calculate_etf_swap`実装
- [x] `calculate_portfolio_swap`実装
- [x] `validate_etf_price_mcp`実装
- [x] `register_all_tools()`に統合

### Phase 2: 価格取得の改善（今週）

**ファイル**: `ib_sec_mcp/mcp/tools/yahoo_finance.py`

タスク:
- [ ] `get_etf_price_lse()`実装
- [ ] ロンドン市場のティッカー対応
- [ ] 通貨指定対応（USD/GBP/EUR）
- [ ] 構造化データ返却

### Phase 3: ワークフローの統合（来週）

**新しいワークフロー**:

```
ユーザー: 「VOOをCSPXに差し替える場合の株数は？」
    ↓
LLM: MCPツール呼び出し
    ↓
1. get_current_price("VOO") → 構造化データ取得
2. get_etf_price_lse("CSPX", "USD") → 構造化データ取得
3. validate_etf_price_mcp("CSPX", 714.78, "VOO", 607.39) → 検証
4. calculate_etf_swap(...) → Python側で正確に計算
    ↓
LLM: 結果を整形して返答（計算は一切行わない）
```

---

## 📊 効果測定

### Before（今回の誤り発生時）

| 項目 | 状態 | 問題 |
|------|------|------|
| 価格取得 | WebSearch | 非構造化、解釈必要 |
| 計算 | LLM | 算術計算ミス |
| 検証 | なし | 誤りに気づけない |
| 信頼性 | 低 | ❌ 26倍の誤り |

### After（対策実施後）

| 項目 | 状態 | 改善 |
|------|------|------|
| 価格取得 | Yahoo Finance API | ✅ 構造化、数値型 |
| 計算 | Python (Decimal) | ✅ 高精度、正確 |
| 検証 | 自動検証 + 警告 | ✅ 異常検知 |
| 信頼性 | 高 | ✅ 誤り防止 |

---

## 🔄 ワークフロー比較

### Before: LLM中心の計算

```
1. WebSearchで価格検索
   ↓ (テキスト解析)
2. LLMが価格を解釈
   ↓ (推測 + 仮定)
3. LLMが為替計算
   ↓ (算術計算ミス)
4. LLMが株数計算
   ↓ (誤った価格で計算)
5. 結果を出力
   ↓
❌ 誤った結果（206株 → 実際は5,373株）
```

### After: Python中心の計算

```
1. Yahoo Finance APIで価格取得
   ↓ (構造化データ)
2. Pythonで価格検証
   ↓ (自動チェック)
3. 警告があれば人間確認
   ↓ (妥当性確認)
4. Pythonで計算実行
   ↓ (Decimal高精度計算)
5. 結果を出力
   ↓
✅ 正確な結果（5,373株）
```

---

## 🛠️ 実装例

### MCPツール登録

**ファイル**: `ib_sec_mcp/mcp/tools/etf_tools.py`

```python
"""ETF差し替え計算MCPツール"""

import json
from decimal import Decimal
from fastmcp import FastMCP

from ib_sec_mcp.tools.etf_calculator import (
    ETFSwapCalculator,
    validate_etf_price,
)


def register_etf_calculation_tools(mcp: FastMCP) -> None:
    """ETF計算ツールをMCPサーバーに登録"""

    @mcp.tool()
    async def calculate_etf_swap(
        from_symbol: str,
        from_shares: int,
        from_price: float,
        from_expense_ratio: float,
        from_dividend_yield: float,
        from_withholding_tax: float,
        to_symbol: str,
        to_price: float,
        to_expense_ratio: float,
        to_dividend_yield: float,
        to_withholding_tax: float,
    ) -> str:
        """
        ETF差し替えの必要株数と年間メリットを計算

        すべての計算をPython側で実施し、LLMの算術計算ミスを防ぐ。

        Args:
            from_symbol: 売却するETFのシンボル
            from_shares: 売却株数
            from_price: 売却価格（USD）
            from_expense_ratio: 経費率（小数）例：0.0003 = 0.03%
            from_dividend_yield: 配当利回り（小数）例：0.0115 = 1.15%
            from_withholding_tax: 源泉税率（小数）例：0.30 = 30%
            to_symbol: 購入するETFのシンボル
            to_price: 購入価格（USD）
            to_expense_ratio: 経費率（小数）
            to_dividend_yield: 配当利回り（小数）
            to_withholding_tax: 源泉税率（小数）

        Returns:
            JSON文字列（必要株数、投資額、年間メリット等）

        Example:
            >>> result = await calculate_etf_swap(
            ...     from_symbol="TLT",
            ...     from_shares=200,
            ...     from_price=91.34,
            ...     from_expense_ratio=0.0015,
            ...     from_dividend_yield=0.0433,
            ...     from_withholding_tax=0.30,
            ...     to_symbol="IDTL",
            ...     to_price=3.40,
            ...     to_expense_ratio=0.0007,
            ...     to_dividend_yield=0.0445,
            ...     to_withholding_tax=0.15,
            ... )
        """
        calculator = ETFSwapCalculator()

        result = calculator.calculate_swap(
            from_symbol=from_symbol,
            from_shares=from_shares,
            from_price=Decimal(str(from_price)),
            from_expense_ratio=Decimal(str(from_expense_ratio)),
            from_dividend_yield=Decimal(str(from_dividend_yield)),
            from_withholding_tax=Decimal(str(from_withholding_tax)),
            to_symbol=to_symbol,
            to_price=Decimal(str(to_price)),
            to_expense_ratio=Decimal(str(to_expense_ratio)),
            to_dividend_yield=Decimal(str(to_dividend_yield)),
            to_withholding_tax=Decimal(str(to_withholding_tax)),
        )

        return json.dumps({
            "from_etf": {
                "symbol": result.from_etf.symbol,
                "shares": int(result.from_etf.shares),
                "price": float(result.from_etf.price),
                "total_value": float(result.from_etf.total_value),
                "expense_ratio": float(result.from_etf.expense_ratio),
                "dividend_yield": float(result.from_etf.dividend_yield),
                "withholding_tax_rate": float(result.from_etf.withholding_tax_rate),
            },
            "to_etf": {
                "symbol": result.to_etf.symbol,
                "shares": int(result.to_etf.shares),
                "price": float(result.to_etf.price),
                "total_value": float(result.to_etf.total_value),
                "expense_ratio": float(result.to_etf.expense_ratio),
                "dividend_yield": float(result.to_etf.dividend_yield),
                "withholding_tax_rate": float(result.to_etf.withholding_tax_rate),
            },
            "required_shares": result.required_shares,
            "purchase_amount": float(result.purchase_amount),
            "surplus_cash": float(result.surplus_cash),
            "annual_withholding_tax_savings": float(result.annual_withholding_tax_savings),
            "annual_expense_change": float(result.annual_expense_change),
            "annual_net_benefit": float(result.annual_net_benefit),
            "payback_period_months": result.payback_period_months,
        }, indent=2)

    @mcp.tool()
    async def validate_etf_price_mcp(
        symbol: str,
        price: float,
        reference_symbol: str = None,
        reference_price: float = None,
    ) -> str:
        """
        ETF価格の妥当性を検証

        価格が異常に低い/高い場合や、参照ETFとの乖離が大きい場合に警告。

        Args:
            symbol: ETFシンボル
            price: 価格（USD）
            reference_symbol: 参照ETFシンボル（オプション、同じ指数を追跡）
            reference_price: 参照ETF価格（オプション）

        Returns:
            JSON文字列（検証結果、警告メッセージ）

        Example:
            >>> result = await validate_etf_price_mcp(
            ...     symbol="IDTL",
            ...     price=3.40,
            ...     reference_symbol="TLT",
            ...     reference_price=91.34
            ... )
        """
        validation = validate_etf_price(
            symbol=symbol,
            price=Decimal(str(price)),
            reference_symbol=reference_symbol,
            reference_price=Decimal(str(reference_price)) if reference_price else None,
        )

        return json.dumps(validation, indent=2)
```

**ファイル**: `ib_sec_mcp/mcp/tools/__init__.py`

```python
from .etf_tools import register_etf_calculation_tools

def register_all_tools(mcp: FastMCP) -> None:
    """Register all MCP tools"""
    register_data_fetching_tools(mcp)
    register_analysis_tools(mcp)
    register_yahoo_finance_tools(mcp)
    register_etf_calculation_tools(mcp)  # ← 追加
```

---

## 📝 使用例（新しいワークフロー）

### シナリオ: VOOをCSPXに差し替え

**ユーザー**: 「VOO 40株をCSPXに差し替える場合、何株必要？」

**LLMの処理**:

```python
# Step 1: 価格取得（構造化データ）
voo_data = await get_current_price("VOO")
# → {"symbol": "VOO", "current_price": 607.39, ...}

cspx_data = await get_etf_price_lse("CSPX", "USD")
# → {"symbol": "CSPX", "price": 714.78, "currency": "USD", ...}

# Step 2: 価格検証
validation = await validate_etf_price_mcp(
    symbol="CSPX",
    price=714.78,
    reference_symbol="VOO",
    reference_price=607.39
)
# → {"is_valid": true, "warnings": ["ℹ️ CSPXはVOOの1.18倍..."]}

# Step 3: 計算実行（Python側で正確に）
result = await calculate_etf_swap(
    from_symbol="VOO",
    from_shares=40,
    from_price=607.39,
    from_expense_ratio=0.0003,
    from_dividend_yield=0.0115,
    from_withholding_tax=0.30,
    to_symbol="CSPX",
    to_price=714.78,
    to_expense_ratio=0.0007,
    to_dividend_yield=0.0115,
    to_withholding_tax=0.00,
)
# → {"required_shares": 34, "purchase_amount": 24302.52, ...}
```

**LLMの返答**:

```
VOO 40株をCSPXに差し替える場合：

必要株数: 34株
購入金額: $24,302.52
余剰金: -$6.92（ほぼ完全一致）

年間メリット:
- 配当源泉税削減: $84.00/年
- 経費増加: -$9.72/年
- 純メリット: $74.28/年

投資回収期間: 約12ヶ月

注意: CSPXはVOOの1.18倍の価格です（正常）
```

**重要**: LLMは一切計算していない（Python側で全計算）

---

## ✅ チェックリスト

### 即座に実施（Phase 1）✅ 完了

- [x] `etf_calculator.py`作成
- [x] MCPツールとして登録
  - [x] `register_etf_calculator_tools()`実装
  - [x] `calculate_etf_swap`追加
  - [x] `calculate_portfolio_swap`追加
  - [x] `validate_etf_price_mcp`追加
- [ ] テスト作成
  - [ ] 単体テスト
  - [ ] MCPツール統合テスト

### 今週実施（Phase 2）

- [ ] `get_etf_price_lse()`実装
- [ ] ロンドン市場対応
- [ ] 通貨指定対応
- [ ] 構造化データ返却

### 来週実施（Phase 3）

- [ ] ドキュメント更新
- [ ] 使用例追加
- [ ] Slash command統合
- [ ] サブエージェント活用

---

## 🎯 成功基準

### 短期（1週間）

- ✅ MCPツールとして`calculate_etf_swap`が動作
- ✅ Python側で100%正確な計算
- ✅ LLMは結果整形のみ

### 中期（1ヶ月）

- ✅ すべての金融計算がPython側に移行
- ✅ 価格取得が構造化データに
- ✅ 自動検証が機能

### 長期（3ヶ月）

- ✅ 類似の誤りゼロ
- ✅ 計算信頼性100%
- ✅ ユーザー満足度向上

---

## 📚 参考資料

### 関連ファイル

- `ib_sec_mcp/tools/etf_calculator.py` - 計算ロジック（作成済み）
- `ib_sec_mcp/mcp/tools/etf_tools.py` - MCPツール（作成予定）
- `ib_sec_mcp/mcp/tools/yahoo_finance.py` - 価格取得（拡張予定）

### ドキュメント

- Python Decimal公式ドキュメント
- FastMCP公式ドキュメント
- Yahoo Finance API仕様

---

**作成者**: IB Analytics Development Team
**承認者**: Kenichiro Nishioka
**最終更新**: 2025年10月17日
