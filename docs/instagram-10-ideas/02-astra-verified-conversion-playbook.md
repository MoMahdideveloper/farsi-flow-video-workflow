# Stage 2 — Verified Conversion Playbook / برنامه تبدیل مخاطب به مشتری

For [@kelidbox_com](https://www.instagram.com/kelidbox_com/) → [KelidBox](https://kelidbox.com).

## 1. Conversion audit and evidence boundary

**Verified means offline consistency, not a fresh live-store or platform-policy audit.** Reviewed 2026-10-26 using the [catalog context](00-kelidbox-instagram-and-catalog-context.md), [Stage 1 scripts](01-opus55-10-instagram-conversion-ideas.md) and [manifest](../../pipeline/manifests/instagram_10_conversion_ideas.json). No web searches or external HTTP fetches were performed. Coupon rules and TorobPay / DigiPay availability are explicitly user-confirmed in the Stage-2 request; the older context mentions SnappPay. Prefer the newer instruction; do not advertise SnappPay here.

The context reports 263 total catalog products but contains an abbreviated listing, not 263 individually enumerated rows. Validate only IDs actually listed. Prices are recorded starting prices, not current quotes or combined bundle costs.

### Audit findings and fixes

| Finding | Conversion risk | Resolution |
|---|---|---|
| CapCut Pro, Wordwall Pro, Office 365 absent from seeded rows | Invalid offer and false low-price anchors | Removed from featured listings and regenerated both deliverables |
| Cheapest accessory used as entry cost | HeyGen demo advertised at Canva price | One explicit primary product and matching price per idea |
| Long hooks; first shot differed from hook | Promise arrives too late | Short Persian hook appears and is spoken in first 3 seconds; audio timing still needs render QA |
| Unsupported instant delivery, two-click completion, zero-interest promises | Checkout disappointment | Use actual delivery, credit and checkout terms; no unconditional promises |
| Guaranteed income, ping reduction and perfect academic outcomes | Misleading demonstrations | Replace with sample portfolio, region checks and reviewed draft outcomes |
| Product IDs but no verified permalinks | Broken DM destination | Candidate links below; automation stays OFF until real URLs are checked |
| Idea-level JSON mistaken for render-ready input | Broken pipeline | Planning schema only; clips and subtitle retiming required before build |

**Offer used throughout:** WELCOME10 = 10% off, maximum 150,000 Toman, minimum order 100,000 Toman. At 380,000 the arithmetic saving is 38,000; at 1,710,000 it is capped at 150,000, not 171,000. Do not split a basket to multiply a coupon. Four installments are offered through TorobPay / DigiPay subject to eligibility. Coupon stacking, fees, exact due dates and first payment are not independently checked.

### Priority ranking matrix — all 10 ideas

These are editorial hypotheses, not measured conversion rates. Each dimension scores 1–5. Viral Reach: narrow → broad/shareable; Beginner Clarity: abstract → immediately understandable; Ticket Size: higher primary-product starting price → higher potential order value (not profit); Conversion Speed: education-heavy → obvious near-term need. Ticket bands: 1 < 1m; 2 = 1–<1.5m; 3 = 1.5–<3m; 4 = 3–<5m; 5 ≥ 5m Toman.

**Priority = 20% Reach + 25% Clarity + 15% Ticket + 40% Speed.** Clarity and purchase intent outweigh expensive products. No revenue forecast is implied.

| Rank | Idea ID / keyword | Viral Reach | Beginner Clarity | Ticket Size | Conversion Speed | Weighted / 5 | Primary price, Toman | Why / constraint |
|---|---|---|---|---|---|---|---|---|
| 1 | IG10_01 / تیزر | 4 | 5 | 3 | 5 | 4.50 | 1,710,000 | Concrete store problem; show unchanged product details |
| 2 | IG10_02 / انیمیشن | 5 | 4 | 3 | 5 | 4.45 | 1,710,000 | Closest bridge from existing animation audience |
| 3 | IG10_06 / اسلاید | 4 | 5 | 3 | 4 | 4.10 | 2,200,000 | Deadline-driven need; review all facts and sources |
| 4 | IG10_05 / نقاشی | 5 | 5 | 3 | 3 | 3.90 | 1,710,000 | Strong family appeal; parent consent and child privacy |
| 5 | IG10_09 / بدون تبلیغ | 4 | 5 | 4 | 3 | 3.85 | 4,360,000 | Clear pain; YouTube offer must not use cheaper Disney price |
| 6 | IG10_08 / قیمت | 3 | 4 | 1 | 5 | 3.75 | 380,000 | Use as retargeting FAQ, not cold-audience first impression |
| 7 | IG10_04 / تولد | 5 | 5 | 4 | 2 | 3.65 | 4,850,000 | Shareable gift, but expensive for one occasion; song first, video optional |
| 8 | IG10_07 / درآمد | 4 | 4 | 1 | 4 | 3.55 | 380,000 | Low entry cost; needs portfolio-building, not income promises |
| 9 | IG10_10 / گیم | 4 | 4 | 2 | 3 | 3.30 | 1,140,000 | Region and parental checks; no debt pressure or performance claims |
| 10 | IG10_03 / مجری | 3 | 4 | 5 | 2 | 3.15 | 8,730,000 | Higher ticket; avatar consent and Persian quality check |

### Publish these three Reels FIRST

1. **IG10_01 — تیزر:** phone photo → short product ad; comment تیزر. Lead with a real before/after on the same product. No sales-uplift guarantee.
2. **IG10_02 — انیمیشن:** recognizable fruit characters → show the creator's hands, not face; comment انیمیشن. Converts existing story curiosity into a personal use case.
3. **IG10_06 — اسلاید:** blank deck → reviewed draft; comment اسلاید. Fast, concrete non-video use case broadens catalog understanding.

Publish on calendar days 2, 4 and 6. Do not lead with ten products or a catalog tour. One Reel = one problem, one primary account, one keyword. Keep secondary tools in optional follow-up, not required bundles.

## 2. Profile makeover: bio, three pinned posts, five highlights

### Copy-paste Persian bio

```text
🎬 از انیمیشن تا ایده برای کار تو
🛒 اکانت AI و سرگرمی
💳 ۴ قسط، طبق شرایط درگاه
🎁 WELCOME10؛ شرایط در سایت ↓
```

Use the profile website field for [KelidBox](https://kelidbox.com), rather than wasting bio space on a non-clickable URL. Display name: «کلیدباکس | اکانت AI و آموزش کاربردی». Keep trust proof in the highlight, not as a substitute for showing product fit.

### Pinned post 1 — این انیمیشن به درد من چی می‌خوره؟ (40s)

| Time | Visual / exact Persian speech | Overlay / next action |
|---|---|---|
| 0–3 | Fruit-series freeze → product ad. «این کارتون، فقط سرگرمی نیست!» | «برای کار تو هم کاربرد داره» |
| 3–12 | Same photo of a shoe becomes a motion demo. «مغازه داری؟ از عکس محصولت یک نمونه تیزر بساز.» | «عکس ← نمونه تیزر» |
| 12–22 | Hands at laptop writing a story. «جلوی دوربین راحت نیستی؟ یک داستان کوتاه بدون چهره امتحان کن.» | «ایده ← انیمیشن» |
| 22–32 | Actual Google AI Pro listing, not generated UI. «ابزار این نمونه رو در کلیدباکس ببین؛ پلن و محدودیت‌ها رو بخون.» | Product name, no invented badge |
| 32–40 | Point to comments. «تیزر رو کامنت کن؛ لینک و شرایط تخفیف رو می‌فرستیم.» | «تیزر»؛ caption contains full offer |

### Pinned post 2 — اولین ویدیوی AI: راهنمای ۳ دقیقه‌ای

A three-minute tutorial, **not a promise that rendering or learning takes three minutes**. Product/Flow access, quota and regional eligibility must be checked for the chosen account before purchase.

| Time | Exact Persian instruction | Demonstration |
|---|---|---|
| 0:00–0:20 | «این راهنما سه دقیقه‌ست؛ زمان ساخت ویدیو به ابزار و صف پردازش بستگی داره.» | Finished 8s example, labelled AI-generated |
| 0:20–0:45 | «یک عکس روشن از محصول خودت انتخاب کن؛ نوشته و جزئیاتش باید معلوم باشه.» | Own product photo; no client or child data |
| 0:45–1:20 | «در بخش تصویر به ویدیو، عکس رو اضافه کن و این دستور رو بنویس.» | Prompt below; actual current interface recording |
| 1:20–1:55 | «یک حرکت ساده بخواه؛ اگر شکل محصول عوض شد، خروجی رو قبول نکن.» | Compare shape, logo, color and texture |
| 1:55–2:25 | «متن فارسی رو در تدوین اضافه کن؛ راست‌به‌چپ و املای متن رو چک کن.» | Add subtitle manually; preview on phone |
| 2:25–2:45 | «برای مشتری، اول اجازه استفاده از عکس و حق انتشار رو بگیر.» | Permission checklist, no income claim |
| 2:45–3:00 | «انیمیشن رو کامنت کن تا لینک ابزار و راهنمای خرید رو بگیری.» | Primary product link via gated DM |

Prompt: «همین محصول را با شکل، رنگ و لوگوی ثابت حفظ کن. دوربین به‌آرامی نزدیک شود، نور نرم، پس‌زمینه ساده، عمودی ۹:۱۶، بدون نوشته داخل تصویر.»

**Mini-lead-magnet delivery:** paste this same seven-step tutorial into the requested DM follow-up; no invented PDF download or nonexistent landing page. Free guidance is not contingent on purchasing an account.

### Pinned post 3 — قبل خرید: قیمت، تخفیف و قسط (40s)

| Time | Exact Persian speech | Proof |
|---|---|---|
| 0–3 | «قیمت نهایی چقدر میشه؟» | Selected product, not cheapest accessory |
| 3–12 | «اول پلن، مدت اشتراک و زمان تحویل رو بخون.» | Real product screen recording |
| 12–22 | «WELCOME10 ده درصد تخفیفه؛ تا صد و پنجاه هزار تومان، با حداقل سفارش صد هزار تومان.» | Large RTL terms; repeat in caption |
| 22–32 | «برای چهار قسط، ترب‌پی یا دیجی‌پی رو انتخاب کن؛ شرایط اعتبار و مبلغ نهایی رو ببین.» | No completed-payment animation presented as real proof |
| 32–40 | «قیمت رو کامنت کن؛ لینک و راهنمای خرید رو می‌فرستیم.» | Link in DM; actual Enamad details in trust highlight |

Caption shared by pinned posts: «کد WELCOME10: ۱۰٪ تخفیف تا سقف ۱۵۰٬۰۰۰ تومان؛ حداقل سفارش ۱۰۰٬۰۰۰ تومان. ۴ قسط ترب‌پی / دیجی‌پی طبق شرایط اعتبار. قبل پرداخت، مبلغ نهایی، امکان ترکیب کد و قسط، سررسیدها و زمان تحویل را بررسی کن.»
