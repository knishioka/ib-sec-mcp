# Claude Code Configuration Validator

静的解析ツールでsub-agentsとslash commandsの設定を自動検証します。

## 機能

### 検証項目

**Sub-Agents**:
- ✅ Frontmatter必須フィールド（name, description, tools, model）
- ✅ Name形式（kebab-case）
- ✅ Model値（opus/sonnet/haiku）
- ✅ Tools権限（MCP tools, Bash, Task等）
- ⚠️ Description品質（長さ、PROACTIVELY推奨）
- ℹ️ 推奨セクション（Workflow, Responsibilities）

**Slash Commands**:
- ✅ Frontmatter必須フィールド（description, allowed-tools）
- ✅ Description長さ（100文字以内推奨）
- ✅ Tools権限（Task, MCP tools）
- ✅ Task委任構文チェック
- ✅ 参照サブエージェント存在確認
- ⚠️ $ARGUMENTS使用時のargument-hint推奨
- ℹ️ 使用例セクション推奨

## 使い方

### 基本使用

```bash
# 全ファイル検証
python3 .claude/scripts/validate_claude_config.py

# 特定ファイル検証
python3 .claude/scripts/validate_claude_config.py .claude/agents/strategy-coordinator.md

# 詳細表示（INFO含む）
python3 .claude/scripts/validate_claude_config.py --verbose
```

### Git統合

```bash
# 変更ファイルのみ検証
python3 .claude/scripts/validate_claude_config.py --changed-only

# Pre-commit hookインストール
ln -sf ../../.claude/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# 動作確認
.git/hooks/pre-commit
```

### CI/CD統合

```bash
# GitHub Actions
- name: Validate Claude Config
  run: python3 .claude/scripts/validate_claude_config.py
```

## 出力例

### 成功例

```
============================================================
Claude Code Configuration Validation Results
============================================================

✅ agents/data-analyzer.md
   ℹ️ Consider adding 'Use PROACTIVELY' for auto-activation
   💡 Add to description if this agent should activate automatically

✅ commands/investment-strategy.md

============================================================
Summary:
  ❌ Errors: 0
  ⚠️ Warnings: 0
  ℹ️ Info: 1
============================================================
```

### エラー例

```
❌ agents/strategy-coordinator.md
   ❌ Missing MCP tool permission
   💡 Add 'mcp__ib-sec-mcp__analyze_consolidated_portfolio' to tools

⚠️ commands/tax-report.md
   ⚠️ Uses Task delegation but Task not in allowed-tools
   💡 Add 'Task' to allowed-tools in frontmatter

============================================================
Summary:
  ❌ Errors: 1
  ⚠️ Warnings: 1
  ℹ️ Info: 0
============================================================
```

## 検証レベル

### Level 1: エラー（❌）
- **必須項目欠落**: frontmatter必須フィールドなし
- **設定矛盾**: Task使用だがallowed-toolsにない
- **参照エラー**: 存在しないサブエージェント参照
- **不正値**: 無効なmodel値

→ **コミットブロック**

### Level 2: 警告（⚠️）
- **形式問題**: name形式がkebab-caseでない
- **設定不備**: $ARGUMENTS使用だがargument-hintなし
- **品質**: Description短すぎる
- **不明ツール**: 未知のツール名

→ **修正推奨**

### Level 3: 情報（ℹ️）
- **ベストプラクティス**: PROACTIVELYキーワード推奨
- **推奨セクション**: Workflow, Responsibilitiesセクション
- **使用例**: Examplesセクション推奨

→ **品質向上**

## トラブルシューティング

### "File not found" エラー

```bash
# プロジェクトルートから実行
cd /Users/ken/Developer/private/ib-sec
python3 .claude/scripts/validate_claude_config.py
```

### "Git not available" エラー

```bash
# Gitリポジトリで実行
git status

# または全ファイルモード使用
python3 .claude/scripts/validate_claude_config.py
```

### 依存関係なし

このスクリプトは**Python標準ライブラリのみ**を使用。
外部パッケージのインストール不要。

## 開発

### テスト

```bash
# 現在の設定を検証
python3 .claude/scripts/validate_claude_config.py --verbose

# 特定ファイルのみ
python3 .claude/scripts/validate_claude_config.py .claude/agents/strategy-coordinator.md
```

### 拡張

新しい検証ルールを追加する場合：

1. `SubAgentValidator.validate()` または `CommandValidator.validate()` を編集
2. `ValidationMessage` でメッセージ追加
3. テストして動作確認

## 今後の拡張予定

- [ ] `--fix` 自動修正機能（common issues）
- [ ] HTML/JSON レポート出力
- [ ] カスタムルール設定（YAML）
- [ ] パフォーマンス最適化
- [ ] より詳細なMCPツール検証

## ライセンス

MIT License
