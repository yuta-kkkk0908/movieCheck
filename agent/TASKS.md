# Movie App - タスク一覧

以下のタスクを順次実装します。各タスクは優先度順に並べています。

1. Improve /authorize/done navigation (univLink handling)
   - `/authorize/done` ページの `a.univLink` を安全に検出してクリック
   - リダイレクト先の URL から `user_id` を抽出して `/user/{user_id}/movie/` へ遷移
   - 失敗時のフォールバック (XPath, JSリダイレクト)

2. Save credentials & auto-login
   - フロントエンドで映画.com の認証情報保存オプションを追加
   - バックエンドで暗号化して保存し、自動同期時に使用
   - 設定画面（または同期ダイアログ）でログイン情報の管理

3. Show search next to sync button
   - フロントの同期ボタン横に常時表示する検索UIを追加
   - 検索結果は既存の映画登録フローと連携

4. Allow editing/deleting records
   - 視聴記録一覧で `視聴日` / `視聴方法` / `評価` / `気分` を編集可能にする
   - 記録の削除機能を追加（UI + API）

5. Add fetch details button (year & cast)
   - 各作品に「作品情報取得」ボタンを追加
   - 押下で `get_movie_details()` を呼び、公開年・出演者を取得して表示/保存

6. Ensure scraper captures director
   - 映画.com のリスト要素（`<p class="sub"> ... 監督`）から監督名を抽出して保存
   - `get_movie_details()` でも補完する

7. Test complete scrape workflow
   - フル同期を実行してログ・データベースの動作を確認
   - 重複登録やエラーハンドリングを重点的に検証

実装方針
- 各タスクを順次実装し、完了したら `TASKS.md` と TODO 管理を更新します。
- まず #1（`/authorize/done` の改善）を完成させ、次に自動ログイン (#2) を取り掛かります。

---

進め方の確認: この順序で着手してよいですか？変更したい優先度があれば教えてください。