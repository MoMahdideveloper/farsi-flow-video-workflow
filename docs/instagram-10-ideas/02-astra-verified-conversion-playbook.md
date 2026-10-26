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

### Five story highlights — exact frame scripts

Use the requested full titles on each opening frame. Short cover labels are پیشنهاد ساخت / درآمد / ۴ قسط / تخفیف / اعتماد if Instagram truncates the full title. Each frame 5–8 seconds; use real screen captures for store or payment claims.

#### 🎬 با AI چی بسازم؟
1. «مغازه داری؟ عکس محصولت رو به نمونه تیزر تبدیل کن.» — same product before/after, no changed features.
2. «دوست نداری جلوی دوربین باشی؟ داستان کوتاه بدون چهره بساز.» — recognizable fruit-series bridge.
3. «ارائه داری؟ از متن درس، پیش‌نویس اسلاید بگیر و بازبینی کن.» — reviewed draft, not a perfect grade.
4. «برای شروع، تیزر یا انیمیشن یا اسلاید رو دایرکت کن.» — route to the matching product only.

#### 💰 درآمد با ویدیو AI
1. «اول نمونه‌کار بساز؛ خرید ابزار به‌تنهایی درآمد نمی‌سازه.» — show clearly labelled fictional cafe brief.
2. «با اجازه صاحب کسب‌وکار، یک نمونه کاور و ویدیوی کوتاه آماده کن.» — do not invent client endorsements.
3. «تعداد خروجی، اصلاحات و حق استفاده رو قبل سفارش مشخص کن.» — one sample scope card.
4. «برای مسیر نمونه‌کار، درآمد رو دایرکت کن. سفارش و درآمد تضمینی نیست.» — Canva starter; no salary screenshots.

#### 💳 خرید قسطی ۴ ماهه
1. «پرداخت ۴ قسط با ترب‌پی یا دیجی‌پی؛ طبق شرایط اعتبار.» — four payments, not a promise of four full months after delivery.
2. «محصول و پلن رو انتخاب کن؛ در تسویه گزینه پرداخت قسطی رو ببین.» — actual checkout screenshot.
3. «مبلغ هر قسط، پیش‌پرداخت احتمالی، کارمزد و تاریخ سررسید رو همان‌جا بررسی کن.» — provider's schedule is authoritative.
4. «گزینه قسط نبود؟ شرایط اعتبار یا محصول رو با پشتیبانی بررسی کن. خرید زیر سن قانونی با والد یا سرپرست.» — do not imply universal eligibility.

#### 🎁 کد تخفیف ۱۰٪
1. «کد: WELCOME10» — copyable Latin code; keep direction LTR inside RTL text.
2. «۱۰٪ تخفیف تا سقف ۱۵۰٬۰۰۰ تومان؛ حداقل سفارش ۱۰۰٬۰۰۰ تومان.» — no “10% on everything” shorthand.
3. «مثال محاسباتی: خرید ۳۸۰٬۰۰۰ تومانی، ۳۸٬۰۰۰ تومان تخفیف؛ مبلغ نهایی را در تسویه ببین.» — not a live quote.
4. «کد رو وارد کن و اعمال‌شدنش رو ببین؛ ترکیب تخفیف و قسط را قبل پرداخت بررسی کن.» — do not promise stacking.

#### 🛡️ نماد اعتماد اینماد
1. «قبل خرید، اطلاعات فروشگاه رو بررسی کن.» — start from the actual [KelidBox website](https://kelidbox.com).
2. «روی نماد داخل سایت بزن و نام و دامنه و اعتبار نمایش‌داده‌شده رو تطبیق بده.» — capture the real verification page; never generate a badge.
3. «شرایط تحویل، پشتیبانی و محصول رو بخون؛ نماد به‌معنی تضمین نتیجه ابزار نیست.» — exact selected-plan conditions.
4. «سؤال داری؟ از مسیر پشتیبانی داخل سایت بپرس؛ رمز حساب و اطلاعات پرداخت رو در کامنت نفرست.» — use genuine consented reviews only; otherwise no testimonial frame.

## 3. Comment-to-DM automation — all 10 ideas

**Implementation status: scripts only; no ManyChat account connected or automation deployed.** Platform permissions, current message-window rules and trigger availability require an operator check before enabling. A comment-triggered private reply does not automatically grant unlimited promotional messaging.

**RELEASE BLOCKER — product permalinks:** the source contains IDs and prices, but no product URL template. All `/product/{id}` destinations below are explicitly **candidate_unverified_route**, not verified direct links. Before copying into active buttons, replace each with the actual matching product permalink and test the exact plan on mobile. Do not send speculative links to customers. Do not treat passing offline tests as proof a URL resolves.

### Setup and safety

- Use one Reel-specific keyword trigger per idea, not a global substring that catches unrelated comments. For new posts enable only after its destination is verified.
- Normalize ي→ی and ك→ک, trim spaces, normalize zero-width non-joiners; match «بدون تبلیغ» as a phrase and allow «بدون‌تبلیغ». Keep a per-user/post dedupe guard. If several keywords appear, ask in DM which use case they want; never send ten links at once.
- Public reply: «راهنمای درخواستی رو دایرکت کردم 🌱 اگر نرسید، همین کلمه رو برامون دایرکت کن.» Use only after successful send. On failure: «برای گرفتن راهنما، همین کلمه رو دایرکت کن.»
- First private message below delivers the requested information. If the platform requires an opening opt-in button, first say «راهنمای درخواستی‌ات آماده‌ست؛ بزن دریافت راهنما.» and use «دریافت راهنما» before sending product details.
- Follow-up only after the user responds/opts in and within the platform's current permitted window. No scheduled unsolicited 24h/48h sales chase, scraping, purchased lists or mass DMs.
- Optional reply after user engagement: «بیشتر برای چه کاری می‌خوای؟ اگر دوست داشتی، کمک می‌کنیم فقط پلن مناسب نیازت رو انتخاب کنی.»
- Stop words: «توقف»، «لغو»، «نفرست». Exact stop reply: «حتماً؛ پیام تبلیغاتی بیشتری نمی‌فرستیم. هر وقت خواستی خودت پیام بده 🌱» Suppress further automated promotional messages.
- Never ask for passwords, payment-card details, identity documents or children's photos in automated DM. Hand off billing/account issues to the actual site's support channel.
- Log only necessary funnel events and consent state, not sensitive message contents. Apply workspace privacy policy and deletion requests; proposed event names below are not an installed tracker.

### Copy-paste instant DM scripts

Each message includes ONE primary product. Prices are deliberately kept out of DM copy so a stale snapshot does not become a live quote. Optional tools are offered only after understanding the use case. Candidate links are shown visibly for audit, not hidden behind a false verified label.

#### DM IG10_01 — تیزر

**Trigger:** «تیزر» · **Product ID:** `draft_0794ef61-67db-4aa0-9cd6-0977addacf48` · **Button:** «دیدن پلن و شرایط خرید». **Link gate:** candidate_unverified_route; replace/verify before sending.

سلام 🌱 برای «تیزر» پیام دادی؛ این هم راه شروع:

برای فروشگاهت، اول یک عکس روشن از محصول خودت آماده کن؛ هدف، ساخت نمونه تیزره نه تضمین فروش.

محصول پیشنهادی: [اشتراک Google AI Pro (Gemini) + ۵ ترابایت — ۶ ماهه روی جیمیل شما](https://kelidbox.com/product/draft_0794ef61-67db-4aa0-9cd6-0977addacf48)

کد WELCOME10 رو در تسویه وارد کن: ۱۰٪ تخفیف تا سقف ۱۵۰٬۰۰۰ تومان، با حداقل سفارش ۱۰۰٬۰۰۰ تومان.

برای پرداخت ۴ قسط، بعد از انتخاب پلن در تسویه ترب‌پی یا دیجی‌پی رو انتخاب کن و مراحل اعتبار رو انجام بده. مبلغ نهایی، امکان ترکیب کد و قسط، سررسیدها و زمان تحویل رو قبل پرداخت بررسی کن؛ شرایط هر پلن و اعتبار ملاکه.

اگه درباره انتخاب پلن سؤال داری، همین‌جا بپرس؛ برای توقف پیام‌ها بنویس «توقف».

#### DM IG10_02 — انیمیشن

**Trigger:** «انیمیشن» · **Product ID:** `draft_0794ef61-67db-4aa0-9cd6-0977addacf48` · **Button:** «دیدن پلن و شرایط خرید». **Link gate:** candidate_unverified_route; replace/verify before sending.

سلام 🌱 برای «انیمیشن» پیام دادی؛ این هم راه شروع:

برای شروع پیج بدون چهره، یک داستان دوخطی بنویس؛ این مسیر از همون انیمیشن‌هایی میاد که تو پیجمون دیدی.

محصول پیشنهادی: [اشتراک Google AI Pro (Gemini) + ۵ ترابایت — ۶ ماهه روی جیمیل شما](https://kelidbox.com/product/draft_0794ef61-67db-4aa0-9cd6-0977addacf48)

کد WELCOME10 رو در تسویه وارد کن: ۱۰٪ تخفیف تا سقف ۱۵۰٬۰۰۰ تومان، با حداقل سفارش ۱۰۰٬۰۰۰ تومان.

برای پرداخت ۴ قسط، بعد از انتخاب پلن در تسویه ترب‌پی یا دیجی‌پی رو انتخاب کن و مراحل اعتبار رو انجام بده. مبلغ نهایی، امکان ترکیب کد و قسط، سررسیدها و زمان تحویل رو قبل پرداخت بررسی کن؛ شرایط هر پلن و اعتبار ملاکه.

اگه درباره انتخاب پلن سؤال داری، همین‌جا بپرس؛ برای توقف پیام‌ها بنویس «توقف».

#### DM IG10_03 — مجری

**Trigger:** «مجری» · **Product ID:** `draft_12bb11ac-8ac4-4875-8529-8a756991a70b` · **Button:** «دیدن پلن و شرایط خرید». **Link gate:** candidate_unverified_route; replace/verify before sending.

سلام 🌱 برای «مجری» پیام دادی؛ این هم راه شروع:

برای مجری دیجیتال، یک متن کوتاه آماده کن؛ کیفیت فارسی و امکانات پلن رو چک کن و فقط از چهره و صدای مجاز استفاده کن.

محصول پیشنهادی: [اشتراک HeyGen Creator و Pro — حساب جدید ۱ ماهه](https://kelidbox.com/product/draft_12bb11ac-8ac4-4875-8529-8a756991a70b)

کد WELCOME10 رو در تسویه وارد کن: ۱۰٪ تخفیف تا سقف ۱۵۰٬۰۰۰ تومان، با حداقل سفارش ۱۰۰٬۰۰۰ تومان.

برای پرداخت ۴ قسط، بعد از انتخاب پلن در تسویه ترب‌پی یا دیجی‌پی رو انتخاب کن و مراحل اعتبار رو انجام بده. مبلغ نهایی، امکان ترکیب کد و قسط، سررسیدها و زمان تحویل رو قبل پرداخت بررسی کن؛ شرایط هر پلن و اعتبار ملاکه.

اگه درباره انتخاب پلن سؤال داری، همین‌جا بپرس؛ برای توقف پیام‌ها بنویس «توقف».

#### DM IG10_04 — تولد

**Trigger:** «تولد» · **Product ID:** `draft_a817f7f0-7513-497c-af44-0cd2863f6045` · **Button:** «دیدن پلن و شرایط خرید». **Link gate:** candidate_unverified_route; replace/verify before sending.

سلام 🌱 برای «تولد» پیام دادی؛ این هم راه شروع:

برای هدیه، اسم و سه خاطره غیرحساس رو آماده کن؛ اول آهنگ بساز، ساخت موزیک‌ویدیو ابزار و هزینه جدا می‌خواد.

محصول پیشنهادی: [اشتراک Suno AI Pro و Premier — روی حساب شما](https://kelidbox.com/product/draft_a817f7f0-7513-497c-af44-0cd2863f6045)

کد WELCOME10 رو در تسویه وارد کن: ۱۰٪ تخفیف تا سقف ۱۵۰٬۰۰۰ تومان، با حداقل سفارش ۱۰۰٬۰۰۰ تومان.

برای پرداخت ۴ قسط، بعد از انتخاب پلن در تسویه ترب‌پی یا دیجی‌پی رو انتخاب کن و مراحل اعتبار رو انجام بده. مبلغ نهایی، امکان ترکیب کد و قسط، سررسیدها و زمان تحویل رو قبل پرداخت بررسی کن؛ شرایط هر پلن و اعتبار ملاکه.

اگه درباره انتخاب پلن سؤال داری، همین‌جا بپرس؛ برای توقف پیام‌ها بنویس «توقف».

#### DM IG10_05 — نقاشی

**Trigger:** «نقاشی» · **Product ID:** `draft_0794ef61-67db-4aa0-9cd6-0977addacf48` · **Button:** «دیدن پلن و شرایط خرید». **Link gate:** candidate_unverified_route; replace/verify before sending.

سلام 🌱 برای «نقاشی» پیام دادی؛ این هم راه شروع:

برای نقاشی متحرک، با اجازه والدین از خود نقاشی استفاده کن؛ لازم نیست عکس چهره یا اطلاعات کودک رو بفرستی.

محصول پیشنهادی: [اشتراک Google AI Pro (Gemini) + ۵ ترابایت — ۶ ماهه روی جیمیل شما](https://kelidbox.com/product/draft_0794ef61-67db-4aa0-9cd6-0977addacf48)

کد WELCOME10 رو در تسویه وارد کن: ۱۰٪ تخفیف تا سقف ۱۵۰٬۰۰۰ تومان، با حداقل سفارش ۱۰۰٬۰۰۰ تومان.

برای پرداخت ۴ قسط، بعد از انتخاب پلن در تسویه ترب‌پی یا دیجی‌پی رو انتخاب کن و مراحل اعتبار رو انجام بده. مبلغ نهایی، امکان ترکیب کد و قسط، سررسیدها و زمان تحویل رو قبل پرداخت بررسی کن؛ شرایط هر پلن و اعتبار ملاکه.

اگه درباره انتخاب پلن سؤال داری، همین‌جا بپرس؛ برای توقف پیام‌ها بنویس «توقف».

#### DM IG10_06 — اسلاید

**Trigger:** «اسلاید» · **Product ID:** `draft_3492cbe3-b83d-408e-8ff1-c2f635dcf811` · **Button:** «دیدن پلن و شرایط خرید». **Link gate:** candidate_unverified_route; replace/verify before sending.

سلام 🌱 برای «اسلاید» پیام دادی؛ این هم راه شروع:

برای ارائه، متن درسی مجاز رو آماده کن؛ خروجی Gamma پیش‌نویسه و باید منبع و متنش رو خودت بررسی کنی.

محصول پیشنهادی: [اشتراک Gamma AI Plus و Pro — حساب آماده ۱ ماهه](https://kelidbox.com/product/draft_3492cbe3-b83d-408e-8ff1-c2f635dcf811)

کد WELCOME10 رو در تسویه وارد کن: ۱۰٪ تخفیف تا سقف ۱۵۰٬۰۰۰ تومان، با حداقل سفارش ۱۰۰٬۰۰۰ تومان.

برای پرداخت ۴ قسط، بعد از انتخاب پلن در تسویه ترب‌پی یا دیجی‌پی رو انتخاب کن و مراحل اعتبار رو انجام بده. مبلغ نهایی، امکان ترکیب کد و قسط، سررسیدها و زمان تحویل رو قبل پرداخت بررسی کن؛ شرایط هر پلن و اعتبار ملاکه.

اگه درباره انتخاب پلن سؤال داری، همین‌جا بپرس؛ برای توقف پیام‌ها بنویس «توقف».

#### DM IG10_07 — درآمد

**Trigger:** «درآمد» · **Product ID:** `canva-pro` · **Button:** «دیدن پلن و شرایط خرید». **Link gate:** candidate_unverified_route; replace/verify before sending.

سلام 🌱 برای «درآمد» پیام دادی؛ این هم راه شروع:

برای شروع خدمات محتوا، یک نمونه کاور برای کسب‌وکار فرضی بساز؛ خرید ابزار یا این مسیر تضمین درآمد نیست.

محصول پیشنهادی: [اشتراک Canva](https://kelidbox.com/product/canva-pro)

کد WELCOME10 رو در تسویه وارد کن: ۱۰٪ تخفیف تا سقف ۱۵۰٬۰۰۰ تومان، با حداقل سفارش ۱۰۰٬۰۰۰ تومان.

برای پرداخت ۴ قسط، بعد از انتخاب پلن در تسویه ترب‌پی یا دیجی‌پی رو انتخاب کن و مراحل اعتبار رو انجام بده. مبلغ نهایی، امکان ترکیب کد و قسط، سررسیدها و زمان تحویل رو قبل پرداخت بررسی کن؛ شرایط هر پلن و اعتبار ملاکه.

اگه درباره انتخاب پلن سؤال داری، همین‌جا بپرس؛ برای توقف پیام‌ها بنویس «توقف».

#### DM IG10_08 — قیمت

**Trigger:** «قیمت» · **Product ID:** `canva-pro` · **Button:** «دیدن پلن و شرایط خرید». **Link gate:** candidate_unverified_route; replace/verify before sending.

سلام 🌱 برای «قیمت» پیام دادی؛ این هم راه شروع:

برای دیدن مسیر خرید، Canva یک مثال روشنه؛ قیمت این محصول رو با قیمت ابزارهای ویدیویی اشتباه نگیر.

محصول پیشنهادی: [اشتراک Canva](https://kelidbox.com/product/canva-pro)

کد WELCOME10 رو در تسویه وارد کن: ۱۰٪ تخفیف تا سقف ۱۵۰٬۰۰۰ تومان، با حداقل سفارش ۱۰۰٬۰۰۰ تومان.

برای پرداخت ۴ قسط، بعد از انتخاب پلن در تسویه ترب‌پی یا دیجی‌پی رو انتخاب کن و مراحل اعتبار رو انجام بده. مبلغ نهایی، امکان ترکیب کد و قسط، سررسیدها و زمان تحویل رو قبل پرداخت بررسی کن؛ شرایط هر پلن و اعتبار ملاکه.

اگه درباره انتخاب پلن سؤال داری، همین‌جا بپرس؛ برای توقف پیام‌ها بنویس «توقف».

#### DM IG10_09 — بدون تبلیغ

**Trigger:** «بدون تبلیغ» · **Product ID:** `youtube-premium` · **Button:** «دیدن پلن و شرایط خرید». **Link gate:** candidate_unverified_route; replace/verify before sending.

سلام 🌱 برای «بدون تبلیغ» پیام دادی؛ این هم راه شروع:

اگر مسئله‌ات تبلیغ وسط یوتیوبه، این لینک برای YouTube Premium است؛ شرایط منطقه، دستگاه و پلن رو بخون.

محصول پیشنهادی: [اشتراک YouTube Premium + YouTube Music](https://kelidbox.com/product/youtube-premium)

کد WELCOME10 رو در تسویه وارد کن: ۱۰٪ تخفیف تا سقف ۱۵۰٬۰۰۰ تومان، با حداقل سفارش ۱۰۰٬۰۰۰ تومان.

برای پرداخت ۴ قسط، بعد از انتخاب پلن در تسویه ترب‌پی یا دیجی‌پی رو انتخاب کن و مراحل اعتبار رو انجام بده. مبلغ نهایی، امکان ترکیب کد و قسط، سررسیدها و زمان تحویل رو قبل پرداخت بررسی کن؛ شرایط هر پلن و اعتبار ملاکه.

اگه درباره انتخاب پلن سؤال داری، همین‌جا بپرس؛ برای توقف پیام‌ها بنویس «توقف».

#### DM IG10_10 — گیم

**Trigger:** «گیم» · **Product ID:** `cod-mobile-cp` · **Button:** «دیدن پلن و شرایط خرید». **Link gate:** candidate_unverified_route; replace/verify before sending.

سلام 🌱 برای «گیم» پیام دادی؛ این هم راه شروع:

برای CP، اول نسخه Global و شرایط حساب Activision رو تطبیق بده؛ برای زیر سن قانونی، تصمیم خرید و اعتبار با والد یا سرپرسته.

محصول پیشنهادی: [سی‌پی کالاف دیوتی موبایل — نسخه Global، شارژ دستی Activision](https://kelidbox.com/product/cod-mobile-cp)

کد WELCOME10 رو در تسویه وارد کن: ۱۰٪ تخفیف تا سقف ۱۵۰٬۰۰۰ تومان، با حداقل سفارش ۱۰۰٬۰۰۰ تومان.

برای پرداخت ۴ قسط، بعد از انتخاب پلن در تسویه ترب‌پی یا دیجی‌پی رو انتخاب کن و مراحل اعتبار رو انجام بده. مبلغ نهایی، امکان ترکیب کد و قسط، سررسیدها و زمان تحویل رو قبل پرداخت بررسی کن؛ شرایط هر پلن و اعتبار ملاکه.

اگه درباره انتخاب پلن سؤال داری، همین‌جا بپرس؛ برای توقف پیام‌ها بنویس «توقف».
