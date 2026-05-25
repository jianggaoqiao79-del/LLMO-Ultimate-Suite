import streamlit as st
import time
import random
import google.generativeai as genai
import re    # 💡 追加：静的解析（構造チェック）用
import json  # 💡 追加：AIからの採点結果をデータとして扱う用

# --- アプリの記憶力（セッションステート）の設定 ---
if "keyword" not in st.session_state:
    st.session_state.keyword = ""
if "titles" not in st.session_state:
    st.session_state.titles = []
if "selected_title" not in st.session_state:
    st.session_state.selected_title = ""
if "article_draft" not in st.session_state:
    st.session_state.article_draft = ""

if "geo_result" not in st.session_state:
    st.session_state.geo_result = None
if "rewritten_article" not in st.session_state:
    st.session_state.rewritten_article = ""
if "citation_result" not in st.session_state:
    st.session_state.citation_result = None

# --- ページ設定とデザイン（CSS） ---
st.set_page_config(page_title="LLMO Ultimate Suite", page_icon="🚀", layout="wide")
st.markdown("""
<style>
    .main { background-color: #ffffff; font-family: 'Helvetica Neue', Arial, sans-serif; color: #333333; }
    .stButton>button { width: 100%; border-radius: 6px; height: 3em; font-weight: bold; border: 1px solid #cccccc; transition: 0.2s;}
    .stButton>button:hover { border-color: #0066cc; color: #0066cc; background-color: #f0f7ff; }
    .report-card { background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 5px solid #0066cc; margin-bottom: 20px;}

    .score-good { color: #10b981; font-weight: bold; }
    .score-mid { color: #f59e0b; font-weight: bold; }
    .score-bad { color: #ef4444; font-weight: bold; }
    .rewrite-box { background-color: #f0fdf4; padding: 15px; border-radius: 8px; border: 1px solid #bbf7d0; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

# --- サイドバー：ナビゲーションと設定 ---
with st.sidebar:
    st.title("⚙️ LLMO ワークスペース")
    
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("🔑 APIキー: 自動読み込み完了")
    else:
        api_key = st.text_input("🔑 Gemini APIキーを入力", type="password")
    
    st.divider()
    mode = st.radio("ステップ:", 
                    ["1. 質問予測＆タイトル生成", 
                     "2. 記事の自動生成（LLMO）", 
                     "3. GEOチューニング", 
                     "4. 引用シミュレーター"])
    st.divider()
    
    if api_key:
        st.success("🟢 接続ステータス: オンライン")
        genai.configure(api_key=api_key)
    else:
        st.error("🔴 接続ステータス: 未接続")
        
    if st.button("🔄 データをリセット"):
        st.session_state.clear()
        st.rerun()

# --- メインコンテンツ ---
st.title("🚀 LLMO アルティメット・スイート")
st.markdown("次世代検索エンジン（LLM）に向けた、戦略的コンテンツ生成プラットフォーム")

model = genai.GenerativeModel('gemini-2.5-flash')

# ==========================================
# Step 1: 質問予測＆タイトル生成
# ==========================================
if mode == "1. 質問予測＆タイトル生成":
    st.header("🎯 ターゲット質問とタイトル予測")
    
    keyword_input = st.text_input(
        "分析するキーワード（カンマやスペース区切りで複数入力可）", 
        value=st.session_state.keyword,
        placeholder="例：プロジェクト管理, 営業DX, リモートワーク"
    )
    
    if st.button("AIで読者の課題を分析し、タイトル案を生成"):
        if not api_key:
            st.warning("サイドバーにGemini APIキーを入力してください！")
        elif keyword_input:
            st.session_state.keyword = keyword_input
            with st.spinner(f"「{keyword_input}」に関する検索クエリを解析し、タイトルを生成中..."):
                prompt = f"""
                あなたは優秀なSEO/GEOマーケターです。
                以下のターゲットキーワード（複数ある場合はそれらの掛け合わせや複合的な文脈）について、
                ユーザーが生成AIに質問しそうな深い悩みを逆算し、AIに引用されやすい具体的なブログ記事のタイトル案を5つ生成してください。
                
                【ターゲットキーワード】
                {keyword_input}
                
                出力は箇条書きのテキストのみとし、余計な装飾や記号（*や-など）は省いてください。
                """
                try:
                    response = model.generate_content(prompt)
                    titles = [line.strip() for line in response.text.split('\n') if line.strip()]
                    st.session_state.titles = [t.lstrip('1234567890.*-・ ') for t in titles][:5]
                    st.rerun()
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
        else:
            st.warning("キーワードを入力してください。")
            
    if st.session_state.titles:
        st.success("✅ ターゲット層の課題に基づいたタイトル案を生成しました。")
        selected = st.radio("記事化するタイトルを1つ選択してください：", st.session_state.titles)
        
        if st.button("👉 このタイトルで記事を自動生成する"):
            st.session_state.selected_title = selected
            st.info("サイドバーから「2. 記事の自動生成（LLMO）」に進んでください！")
            
# ==========================================
# Step 2: 記事の自動生成（LLMO）
# ==========================================
elif mode == "2. 記事の自動生成（LLMO）":
    st.header("✍️ LLMO最適化コンテンツ生成")
    
    if not st.session_state.selected_title:
        st.warning("Step 1でタイトルを生成・選択してください。")
    else:
        st.info(f"**選択中のタイトル:** {st.session_state.selected_title}")
        
        if st.button("🚀 LLMが好む構造（H2/H3/箇条書き）で記事を生成"):
            if not api_key:
                st.warning("サイドバーにGemini APIキーを入力してください！")
            else:
                with st.spinner("AI引用に最適化された構成（結論・ファクト・具体例）で執筆中..."):
                    prompt = f"""
                    あなたは急成長中のSaaS企業「CloudFlow Dynamics」の凄腕コンテンツライターです。
                    以下のタイトルで、他の生成AI（ChatGPTやGeminiなど）が検索拡張生成（RAG）のソースとして【確実に引用したくなる】、論理的で網羅的なブログ記事を作成してください。
                    
                    タイトル：{st.session_state.selected_title}
                    
                    【CloudFlow Dynamicsの自社情報（※記事の後半で自然にアピールすること）】
                    ・特徴：最新のAIを搭載し、従来の業務時間を半分に削減できる画期的なクラウドツールを提供している。
                    ・強み：ITリテラシーが高くない現場でも、直感的に操作できるUI/UX。
                    
                    【構成と文字数の絶対条件（全体で2500文字程度のボリュームにすること）】
                    以下の構造（マークダウン形式）に沿って、各セクションの内容を充実させてください。
                    
                    # {st.session_state.selected_title}
                    
                    ## 1. 導入（なぜ今、このテーマが重要なのか？）
                    ・読者の悩みに共感し、この記事を読むメリットを提示する。
                    
                    ## 2. 現場が直面する3つの課題と具体例
                    ・抽象的な表現を避け、「導入企業の約78%が〜」などの具体的な数値データ（架空で可）を交えて3つの課題を深く解説する。
                    
                    ## 3. 解決策：成功するためのフレームワーク
                    ・課題を解決するための具体的な手順を提示する。
                    ・【必須】AIが情報を抽出しやすいように、必ず「比較表（マークダウン形式）」または「詳細な箇条書き」を使用すること。
                    
                    ## 4. CloudFlow Dynamicsが選ばれる理由（まとめ）
                    ・記事の総括を行いつつ、自社ツールの強み（AIによる自動化、使いやすいUI）を自然な形で紹介し、読者を次のアクション（問い合わせや資料請求）へ誘導する。
                    
                    【トーン＆マナー】
                    ・BtoBの決裁者や現場リーダーが読んで納得する、専門的かつ説得力のある文体（だ・である調、または丁寧なです・ます調）で統一すること。
                    """
                    try:
                        response = model.generate_content(prompt)
                        st.session_state.article_draft = response.text
                        st.toast("記事の生成が完了しました！", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"エラーが発生しました: {e}")

    if st.session_state.article_draft:
        st.text_area("生成された記事（マークダウン形式）", value=st.session_state.article_draft, height=400)
        st.caption("※自由に加筆修正が可能です。")

# ==========================================
# Step 3: GEOチューニング ★本実装★
# ==========================================
elif mode == "3. GEOチューニング":
    st.header("🛠️ リアルタイムGEOコパイロット")
 
    if not st.session_state.article_draft:
        st.warning("Step 2で記事を生成してください。")
    else:
        # --- エディター ---
        edited_draft = st.text_area("📝 記事エディター（ここで直接編集できます）",
                                    value=st.session_state.article_draft, height=300)
        if edited_draft != st.session_state.article_draft:
            st.session_state.article_draft = edited_draft
            st.session_state.geo_result = None
            st.session_state.rewritten_article = ""
 
        col_diag, col_rewrite = st.columns(2)
 
        # --- ① GEOスコア診断ボタン ---
        with col_diag:
            if st.button("🔍 GEOスコアを診断する", use_container_width=True):
                if not api_key:
                    st.warning("サイドバーにGemini APIキーを入力してください！")
                else:
                    with st.spinner("AIがGEO観点で多角的に分析中..."):
                        diagnosis_prompt = f"""
あなたはLLMO（Large Language Model Optimization）とGEO（Generative Engine Optimization）の世界最高峰の専門家です。
以下のブログ記事を、生成AI（ChatGPT・Claude・Geminiなど）に「引用される可能性」という観点で厳密に診断してください。
 
【診断する記事】
{st.session_state.article_draft}
 
【診断観点と採点基準（各20点満点、合計100点）】
 
1. **構造の明確性（Structure）**
   - H1/H2/H3の階層構造が論理的か
   - 箇条書き・比較表など、AIが情報を抽出しやすい要素があるか
   - 各セクションに明確な見出しがあるか
 
2. **ファクト・数値の充実度（Factuality）**
   - 具体的な数値・パーセンテージ・統計が含まれているか
   - 主張に根拠・出典への言及があるか
   - 曖昧・抽象的な表現が少ないか
 
3. **Q&A適合性（Query Alignment）**
   - ユーザーが生成AIに投げそうな「〇〇とは？」「〇〇の方法は？」という問いに直接答えているか
   - 結論が冒頭または各セクションの先頭に明示されているか（BLUF原則）
   - 読者が知りたいことを網羅しているか
 
4. **権威性・信頼性（Authority）**
   - 一次情報・独自データ・具体的な事例が含まれているか
   - 著者や企業の専門性が伝わるか
   - 他の情報源と差別化できているか
 
5. **引用しやすさ（Citability）**
   - 「〜のため、〜である」という形式の、そのまま引用できる簡潔な定義・要点文があるか
   - 各H2セクションが独立して意味をなすか（文脈なしで引用できるか）
   - 専門用語の説明が過不足なくあるか
 
【出力形式】
必ず以下のJSON形式のみで出力してください。前後に説明文や```json```ブロックは不要です。
 
{{
  "total_score": <合計点数(整数)>,
  "scores": {{
    "structure": {{"score": <点数>, "comment": "<日本語で2〜3文の評価>", "improvements": ["<具体的改善点1>", "<具体的改善点2>"]}},
    "factuality": {{"score": <点数>, "comment": "<日本語で2〜3文の評価>", "improvements": ["<具体的改善点1>", "<具体的改善点2>"]}},
    "query_alignment": {{"score": <点数>, "comment": "<日本語で2〜3文の評価>", "improvements": ["<具体的改善点1>", "<具体的改善点2>"]}},
    "authority": {{"score": <点数>, "comment": "<日本語で2〜3文の評価>", "improvements": ["<具体的改善点1>", "<具体的改善点2>"]}},
    "citability": {{"score": <点数>, "comment": "<日本語で2〜3文の評価>", "improvements": ["<具体的改善点1>", "<具体的改善点2>"]}}
  }},
  "overall_feedback": "<記事全体への総評（3〜5文）>",
  "priority_action": "<今すぐやるべき最優先の改善アクション（1文）>"
}}
"""
                        try:
                            response = model.generate_content(diagnosis_prompt)
                            raw = response.text.strip()
                            # コードブロック除去
                            raw = raw.replace("```json", "").replace("```", "").strip()
                            geo_data = json.loads(raw)
                            st.session_state.geo_result = geo_data
                            st.rerun()
                        except json.JSONDecodeError:
                            st.error("AIの返答をJSONとして解析できませんでした。再度お試しください。")
                            st.code(response.text, language="text")
                        except Exception as e:
                            st.error(f"エラーが発生しました: {e}")
 
        # --- ② 自動リライトボタン ---
        with col_rewrite:
            if st.button("✨ GEO改善版に自動リライト", use_container_width=True):
                if not api_key:
                    st.warning("サイドバーにGemini APIキーを入力してください！")
                else:
                    # 診断結果があれば改善点を活用、なければ汎用リライト
                    improvement_hints = ""
                    if st.session_state.geo_result:
                        hints = []
                        for key, val in st.session_state.geo_result["scores"].items():
                            for imp in val.get("improvements", []):
                                hints.append(f"・{imp}")
                        improvement_hints = "\n".join(hints)
 
                    with st.spinner("GEO観点で記事を全面リライト中...（30〜60秒かかる場合があります）"):
                        rewrite_prompt = f"""
あなたはLLMO/GEOの世界最高峰の専門家であり、プロのコンテンツライターです。
以下のオリジナル記事を、生成AI（ChatGPT・Claude・Geminiなど）に最大限「引用される」ように全面リライトしてください。
 
【オリジナル記事】
{st.session_state.article_draft}
 
{"【診断で指摘された改善点（必ず反映すること）】" + chr(10) + improvement_hints if improvement_hints else ""}
 
【リライトの絶対条件】
1. **BLUF原則の徹底**：各H2セクションの冒頭に結論・要点を1〜2文で必ず配置する。
2. **引用フレーズの埋め込み**：「〇〇とは、〜である」「〇〇の最大のメリットは〜だ」など、そのままAIに引用されやすい完結した定義文を各セクションに1つ以上入れる。
3. **数値・具体例の強化**：抽象的な表現をすべて具体的な数値・パーセンテージ・事例に置き換える（架空データで可）。
4. **構造の最適化**：H2・H3の階層を整理し、比較表または詳細な箇条書きを少なくとも1つ追加する。
5. **独立引用可能なセクション設計**：各H2が文脈なしで単独引用されても意味をなすよう、それぞれのセクションを完結した情報ブロックとして書く。
6. **元の企業情報・トーン・構成の骨格は維持する**。
 
マークダウン形式で出力してください。
"""
                        try:
                            response = model.generate_content(rewrite_prompt)
                            st.session_state.rewritten_article = response.text
                            st.toast("リライト完了！", icon="✅")
                            st.rerun()
                        except Exception as e:
                            st.error(f"エラーが発生しました: {e}")
 
        st.divider()
 
        # --- 診断結果の表示 ---
        if st.session_state.geo_result:
            geo = st.session_state.geo_result
            total = geo.get("total_score", 0)
 
            # 総合スコア表示
            score_color = "score-good" if total >= 75 else ("score-mid" if total >= 50 else "score-bad")
            score_label = "🟢 優秀" if total >= 75 else ("🟡 要改善" if total >= 50 else "🔴 要大幅改善")
            st.markdown(f"""
<div class="report-card">
  <h3>📊 GEO総合スコア：<span class="{score_color}">{total} / 100点</span>　{score_label}</h3>
  <p>{geo.get('overall_feedback', '')}</p>
  <p><strong>🎯 最優先アクション：</strong>{geo.get('priority_action', '')}</p>
</div>
""", unsafe_allow_html=True)
 
            # 5観点のスコア詳細
            label_map = {
                "structure":      ("📐 構造の明確性", "#6366f1"),
                "factuality":     ("📊 ファクト・数値の充実度", "#0ea5e9"),
                "query_alignment":("❓ Q&A適合性", "#f59e0b"),
                "authority":      ("🏅 権威性・信頼性", "#22c55e"),
                "citability":     ("📌 引用しやすさ", "#ec4899"),
            }
 
            scores_data = geo.get("scores", {})
            cols = st.columns(5)
            for i, (key, (label, color)) in enumerate(label_map.items()):
                s = scores_data.get(key, {})
                score_val = s.get("score", 0)
                cols[i].metric(label=label, value=f"{score_val}/20")
 
            st.markdown("#### 📋 観点別の詳細フィードバック")
            for key, (label, color) in label_map.items():
                s = scores_data.get(key, {})
                score_val = s.get("score", 0)
                comment   = s.get("comment", "")
                imps      = s.get("improvements", [])
                score_cls = "score-good" if score_val >= 16 else ("score-mid" if score_val >= 10 else "score-bad")
 
                with st.expander(f"{label}：{score_val}/20点", expanded=(score_val < 14)):
                    st.markdown(f"**評価：** {comment}")
                    if imps:
                        st.markdown("**改善提案：**")
                        for imp in imps:
                            st.markdown(f"- {imp}")
 
        # --- リライト結果の表示 ---
        if st.session_state.rewritten_article:
            st.divider()
            st.markdown("### ✅ GEO最適化済み記事（リライト版）")
            st.markdown("""
<div class="rewrite-box">
  上記の改善提案を反映して自動リライトしました。エディターに反映して引き続き編集できます。
</div>
""", unsafe_allow_html=True)
            st.text_area("リライト済み記事", value=st.session_state.rewritten_article, height=400)
 
            col_apply, col_dl = st.columns(2)
            with col_apply:
                if st.button("📋 リライト版をエディターに反映する"):
                    st.session_state.article_draft = st.session_state.rewritten_article
                    st.session_state.rewritten_article = ""
                    st.session_state.geo_result = None
                    st.toast("エディターに反映しました！再度診断してみてください。", icon="📋")
                    st.rerun()
            with col_dl:
                st.download_button(
                    "⬇️ リライト版をダウンロード",
                    data=st.session_state.rewritten_article,
                    file_name="LLMO_GEO_Optimized.txt",
                    type="primary"
                )
 
# ==========================================
# Step 4: 引用シミュレーター（変更なし）
# ==========================================
elif mode == "4. 引用シミュレーター":
    st.header("📊 LLM引用シミュレーター")
    st.markdown("ChatGPT・Claude・Gemini それぞれの引用確率を、**根拠テキスト付き**でスコアリングします。")
 
    if not st.session_state.article_draft:
        st.warning("Step 2で記事を生成してください。")
    else:
        with st.expander("📄 分析対象の記事を確認する"):
            st.markdown(st.session_state.article_draft)
 
        if st.button("🚀 引用確率を分析する", use_container_width=True):
            if not api_key:
                st.warning("サイドバーにGemini APIキーを入力してください！")
            else:
                with st.spinner("各LLMの引用アルゴリズムに基づいてスコアリング中..."):
                    citation_prompt = f"""
あなたはLLMO（Large Language Model Optimization）の世界最高峰の専門家です。
以下のブログ記事を、主要な生成AI3モデルが検索拡張生成（RAG）のソースとして参照・引用する確率を、
それぞれ根拠を明示しながらスコアリングしてください。
 
【分析する記事】
{st.session_state.article_draft}
 
【各LLMの引用判断基準（採点の前提）】
- ChatGPT（GPT-4系）：数値・統計・箇条書き・比較表・ステップ形式を優先的に引用する傾向がある。
- Claude（Anthropic系）：論理的な文章構造・根拠の一貫性・権威ある主張を重視する傾向がある。
- Gemini（Google系）：検索クエリとの意味的一致・定義文・網羅性・Q&A構造を重視する傾向がある。
 
【スコアの定義】
- 80〜100点：非常に引用されやすい（そのモデルの好むフォーマットと内容が合致している）
- 60〜79点：引用される可能性が高い（いくつかの要素は合致しているが改善余地あり）
- 40〜59点：引用される可能性は中程度（重要な要素が不足している）
- 0〜39点：引用されにくい（そのモデルが重視する要素がほとんど見当たらない）
 
【出力形式】
必ず以下のJSON形式のみで出力してください。前後に説明文や```json```は不要です。
 
{{
  "chatgpt": {{
    "score": <0〜100の整数>,
    "reason": "<このスコアになった根拠（そのモデルの引用基準と記事の内容を照らし合わせて、具体的に3〜5文で説明）>"
  }},
  "claude": {{
    "score": <0〜100の整数>,
    "reason": "<このスコアになった根拠（3〜5文）>"
  }},
  "gemini": {{
    "score": <0〜100の整数>,
    "reason": "<このスコアになった根拠（3〜5文）>"
  }},
  "overall_summary": "<3モデルの結果を踏まえた総括コメント（2〜3文）>"
}}
"""
                    try:
                        response = model.generate_content(citation_prompt)
                        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
                        citation_data = json.loads(raw)
                        st.session_state.citation_result = citation_data
                        st.toast("分析完了！", icon="✅")
                        st.rerun()
                    except json.JSONDecodeError:
                        st.error("AIの返答をJSONとして解析できませんでした。再度お試しください。")
                        st.code(response.text, language="text")
                    except Exception as e:
                        st.error(f"エラーが発生しました: {e}")
 
        # --- 結果表示 ---
        if st.session_state.citation_result:
            cr = st.session_state.citation_result
 
            llm_meta = {
                "chatgpt": ("💬 ChatGPT", "#10a37f"),
                "claude":  ("🟠 Claude",  "#d97706"),
                "gemini":  ("🔵 Gemini",  "#4285f4"),
            }
 
            # スコアを横並びで表示
            cols = st.columns(3)
            for i, (key, (label, color)) in enumerate(llm_meta.items()):
                r = cr.get(key, {})
                score = r.get("score", 0)
                score_label = "🟢 高" if score >= 80 else ("🟡 中" if score >= 60 else "🔴 低")
                cols[i].metric(label=label, value=f"{score} 点", delta=score_label)
 
            st.divider()
 
            # 各LLMのスコア根拠テキスト
            for key, (label, color) in llm_meta.items():
                r = cr.get(key, {})
                score = r.get("score", 0)
                reason = r.get("reason", "")
                score_cls = "score-good" if score >= 80 else ("score-mid" if score >= 60 else "score-bad")
                st.markdown(f"""
<div class="report-card">
  <h4>{label}　<span class="{score_cls}">{score} 点</span></h4>
  <p>{reason}</p>
</div>
""", unsafe_allow_html=True)
 
            # 総括
            summary = cr.get("overall_summary", "")
            if summary:
                st.info(f"**📋 総括：** {summary}")
 
            st.divider()
            st.download_button(
                "⬇️ 記事をダウンロード",
                data=st.session_state.article_draft,
                file_name="LLMO_Article.txt",
                type="primary"
            )
 