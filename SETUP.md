# घर की खोज: your one-time setup (about 40 minutes)

Everything else is already built and running on GitHub's free servers. Your laptop can stay off.
These steps need your own logins, so only you can do them. Do them in this order.

## 1. Instagram: make the account Professional (5 min, on your phone)

1. Instagram → your profile → ☰ → **Account type and tools** → **Switch to professional account** → pick **Creator**.
2. Profile → ☰ → **Accounts Centre** → **Accounts** → add your **Facebook Page**, so the two are linked.
3. Set the name to **घर की खोज | Useful Home Finds**.
4. Bio (copy this):
   ```
   घर और किचन के काम के सामान 🏠
   रील में दिखा नंबर 👇 लिंक पर डालो
   ```
5. Link in bio: `https://venus-code.github.io/ghar-ki-khoj/`

## 2. Free real video clips: Pexels key (3 min)

Without this, every reel uses a plain coloured background. With it, each reel shows real kitchen and home footage, which gets far more views.

1. Sign up at https://www.pexels.com/api/ and copy your API key.
2. In the Terminal (in this folder), run the command below and paste the key when it asks:
   ```bash
   gh secret set PEXELS_API_KEY
   ```

## 3. Connect Instagram + Facebook for auto-posting (20 min, laptop)

1. Go to https://developers.facebook.com → **My Apps** → **Create App**.
   Use case: **Other** → type: **Business** → name it `ghar-reels`. It can stay in Development mode, because it only posts to your own accounts.
2. In the app: **App settings → Basic**. Keep the **App ID** and **App Secret** handy.
3. Open **Tools → Graph API Explorer**. Select your app, then **User Token**, and tick these permissions:
   `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`, `business_management`
4. Click **Generate Access Token** and allow everything for your Page and Instagram account. Copy the token.
5. In the Terminal (in this folder), run:
   ```bash
   .venv/bin/python scripts/setup_meta.py
   ```
   Paste the App ID, App Secret and token when it asks. Nothing you type is shown or saved on disk.
   It swaps your token for one that **never expires** and saves it to GitHub.

## 4. Amazon Associates: so you get paid (10 min)

1. Sign up at https://affiliate-program.amazon.in
   Website: `https://venus-code.github.io/ghar-ki-khoj/`. Also add your Instagram profile link.
2. Copy your **tracking ID** (it looks like `yourname-21`).
3. Send the tracking ID to Claude, or put it in `config.json` under `"amazon_tag"` and run:
   ```bash
   .venv/bin/python scripts/build_site.py && git commit -am "add amazon tag" && git push
   ```
⚠️ Amazon closes the account if you don't get **3 sales in the first 180 days**. Reply to every comment and DM with the find number so people actually click.

## 5. Test it once

GitHub → your repo **ghar-ki-khoj** → **Actions** → **Daily reel** → **Run workflow**. Check that the reel appears on Instagram and Facebook within about 5 minutes.

---

## What happens automatically

| When | What |
|---|---|
| Every day, 7:00 PM IST | One new Hindi reel is made (voice, captions, b-roll) and posted to Instagram + Facebook |
| Nov 17, 2026 → May 15, 2027 | 180 days, 60 products, 3 script styles, so no reel repeats exactly |
| After posting | `posted.json` records it, so nothing is ever posted twice |

## Your weekend check (30–60 min)

1. Instagram app → reply to comments and DMs with the product link or find number. **This is where sales happen.**
2. GitHub → Actions: a red ❌ means a day failed. GitHub emails you about it too. Open the failed run, then **Re-run jobs**.
3. Instagram Insights: tell Claude which products got the most views. It will add more products like those to `products.json`.
4. Optional: in the Instagram app, add a trending song at low volume to your best reel.

## When to come back to Claude

- **Token stopped working** (red ❌ with "OAuth" in the error): run step 3 again.
- **Week 2**: add YouTube Shorts.
- **Month 2**: replace products that got no views.
