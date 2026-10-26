"""Audited idea source; regenerate both Markdown and manifest after edits."""

IDEAS = [{'idea_id': 'IG10_06',
  'segment': 'students_thesis_and_office_workers',
  'keyword': 'اسلاید',
  'title_fa': 'از متن درس، پیش\u200cنویس اسلاید قابل بازبینی بساز',
  'persona_fa': 'دانشجوی کارشناسی/ارشد با ارائه و پایان\u200cنامه، و کارمندی که بعد از هر جلسه باید گزارش و '
                'اسلاید تحویل بدهد.',
  'pain_fa': 'شب\u200cبیداری برای پاورپوینت، جزوه\u200cنویسی دستی سر کلاس و جلسه، استرس ددلاین صبح.',
  'trigger': 'استرس ددلاین + رهایی فوری + «کاش زودتر می\u200cدونستم»',
  'hook_visual': "11:58 PM, a 3D student character gets a Telegram message from the professor 'فردا ساعت ۸ ارائه "
                 "۲۰ اسلایدی' — his soul literally leaves his body; then a clock spins and a finished slide deck "
                 'flies out of the laptop. Show the transformation in the FIRST 3 seconds; do not render text in '
                 'the generated image.',
  'hook_fa': 'فردا ارائه داری؟',
  'before_fa': 'صفحه سفید پاورپوینت و یک فایل صوتی ۹۰ دقیقه\u200cای ضبط\u200cشده از کلاس.',
  'after_fa': 'پیش\u200cنویس اسلاید از متن درس در Gamma؛ صحت، منابع و نگارش فارسی را پیش از ارائه بررسی کن. زمان '
              'تولید متغیر است.',
  'products': ['draft_3492cbe3-b83d-408e-8ff1-c2f635dcf811',
               'claude-pro',
               'chatgpt-plus',
               'draft_31ded853-61a6-47d9-b604-8b21c6283217'],
  'shots': [(8,
             "11:58 PM, a 3D student character gets a Telegram message from the professor 'فردا ساعت ۸ ارائه ۲۰ "
             "اسلایدی' — his soul literally leaves his body; then a clock spins and a finished slide deck flies "
             'out of the laptop. Show the transformation in the FIRST 3 seconds; do not render text in the '
             'generated image.',
             '0–3s: reveal the hook immediately. Say in Persian (Farsi): "فردا ارائه داری؟". 3–8s: hold on the '
             'result; no extra dialogue.',
             'فردا ارائه داری؟',
             ['فردا ارائه داری؟']),
            (8,
             '3D Pixar-style animation, soft cinematic lighting, vertical 9:16, warm Iranian everyday setting, '
             'expressive faces, shallow depth of field. The student drags a 90-minute class audio recording into '
             'an AI note-taker app; a one-page Persian summary appears instantly.',
             'Audio waveform compresses into a neat glowing page. Student says in Persian (Farsi): "صدای کلاس رو '
             'دادم به پلاد، یه دقیقه\u200cای خلاصه\u200cش کرد."',
             'صدای کلاس رو دادم به PLAUD، یه دقیقه\u200cای خلاصه\u200cش کرد.',
             ['۹۰ دقیقه کلاس ← ۱ صفحه خلاصه 📝']),
            (8,
             'Laptop close-up: the summary is pasted into Claude/ChatGPT to make an outline, then into Gamma AI; '
             '20 beautiful slides with charts generate one after another.',
             'Slides cascade like cards, timer in corner reads 02:47. Narrator says in Persian (Farsi): "خلاصه رو '
             'دادم به هوش مصنوعی، گاما بیست تا اسلاید شیک ساخت."',
             'خلاصه رو دادم به هوش مصنوعی، Gamma بیست تا اسلاید شیک ساخت.',
             ['۲۰ اسلاید در چند مرحله ⏱️']),
            (8,
             'Vertical 9:16. Student checks a draft slide against class notes, corrects one factual error and '
             'saves locally. No grade or approval claim.',
             'Close-up on review. Say in Persian: "این فقط پیش\u200cنویسه؛ منبع و متنش رو خودت چک کن."',
             'این فقط پیش\u200cنویسه؛ منبع و متنش رو خودت چک کن.',
             ['پیش\u200cنویس، نه تکلیف آماده', 'بازبینی منبع و متن']),
            (8,
             'Vertical 9:16, same character and setting. Hold a clean phone mockup with empty space for a REAL '
             'product screenshot added in editing. Do not generate logos, checkout UI, seals or readable text.',
             'Slow push-in. Say in Persian (Farsi): "«اسلاید» رو کامنت کن؛ لینک و شرایط خرید رو بگیر.". Leave '
             'space for RTL overlays.',
             '«اسلاید» رو کامنت کن؛ لینک و شرایط خرید رو بگیر.',
             ['کامنت: اسلاید',
              'WELCOME10 • ۱۰٪ تا ۱۵۰٬۰۰۰ تومان',
              'حداقل خرید: ۱۰۰٬۰۰۰ تومان',
              '۴ قسط ترب\u200cپی / دیجی\u200cپی؛ طبق شرایط درگاه'])],
  'primary_product_id': 'draft_3492cbe3-b83d-408e-8ff1-c2f635dcf811'},
 {'idea_id': 'IG10_07',
  'segment': 'freelancers_admins_and_youth_income',
  'keyword': 'درآمد',
  'title_fa': 'برای پیشنهاد خدمات محتوا، نمونه\u200cکار بساز؛ درآمد تضمینی نیست',
  'persona_fa': 'جوان ۱۸ تا ۳۰ ساله، بیکار یا دنبال درآمد جانبی، که فقط گوشی یا لپ\u200cتاپ معمولی دارد و طراحی '
                'بلد نیست.',
  'pain_fa': 'فکر می\u200cکند برای ادیتوری باید فتوشاپ و پریمیر و سیستم گرون یاد بگیرد؛ کلاس\u200cهای طراحی گران '
             'و طولانی\u200cاند.',
  'trigger': 'امید به درآمد + «من هم می\u200cتونم» + کار از خانه',
  'hook_visual': 'Vertical 9:16. Young adult shows a before/after cafe post portfolio on an ordinary laptop. No '
                 'bank SMS, client testimonial or payment proof.',
  'hook_fa': 'اولین نمونه\u200cکارت رو بساز!',
  'before_fa': 'عکس تار و بی\u200cکیفیت محصول یک کافه + ویدیوی خام لرزان از گوشی صاحب کافه.',
  'after_fa': 'کاور شاخص ریلز با کیفیت 4K، لوگوی تمیز، و ریلز ادیت\u200cشده با زیرنویس و افکت — بسته محتوایی که '
              'صاحب پیج بابتش ماهانه پول می\u200cدهد.',
  'products': ['canva-pro',
               'draft_cb39433a-d659-4cea-affe-1de803238eeb',
               'draft_8f001536-6d8a-4996-84ab-fcc126fbdb1e'],
  'shots': [(8,
             'Vertical 9:16. Young adult shows a before/after cafe post portfolio on an ordinary laptop. No bank '
             'SMS, client testimonial or payment proof.',
             'Immediate portfolio reveal. Say in Persian: "اولین نمونه\u200cکارت رو بساز!".',
             'اولین نمونه\u200cکارت رو بساز!',
             ['اولین نمونه\u200cکارت رو بساز!']),
            (8,
             'Phone screen: a blurry low-res cafe product photo is upscaled by Magnific AI into a crisp 4K image, '
             'then background removed in Picsart with one tap.',
             'Blur-to-sharp wipe transition, sparkle. Character says in Persian (Farsi): "عکس تار مشتری رو با '
             'مگنیفیک فورکی کردم، با پیکس\u200cآرت پس\u200cزمینه\u200cش رو برداشتم."',
             'عکس تار مشتری رو با Magnific فورکی کردم، با Picsart پس\u200cزمینه\u200cش رو برداشتم.',
             ['۱. کیفیت 4K با Magnific 🔍', '۲. حذف پس\u200cزمینه با Picsart']),
            (8,
             'Vertical 9:16. Show a cafe cover designed in Canva, then a timeline with manually added Persian '
             'subtitles. Use real screen capture in editing.',
             'Swipe between cover and timeline. Say in Persian: "کاور رو طراحی کن؛ متن فارسی رو دستی اضافه و '
             'بازبینی کن."',
             'کاور رو طراحی کن؛ متن فارسی رو دستی اضافه و بازبینی کن.',
             ['کاور با Canva', 'زیرنویس فارسی با بازبینی']),
            (8,
             'Vertical 9:16. A freelancer sends a clearly labelled sample portfolio to a cafe owner; owner '
             'considers it, no hiring, handshake or money.',
             'Show the sample. Say in Persian: "نمونه\u200cکارت رو پیشنهاد بده؛ گرفتن سفارش تضمینی نیست."',
             'نمونه\u200cکارت رو پیشنهاد بده؛ گرفتن سفارش تضمینی نیست.',
             ['اول نمونه\u200cکار', 'درآمد تضمینی نیست']),
            (8,
             'Vertical 9:16, same character and setting. Hold a clean phone mockup with empty space for a REAL '
             'product screenshot added in editing. Do not generate logos, checkout UI, seals or readable text.',
             'Slow push-in. Say in Persian (Farsi): "«درآمد» رو کامنت کن؛ لینک و شرایط خرید رو بگیر.". Leave '
             'space for RTL overlays.',
             '«درآمد» رو کامنت کن؛ لینک و شرایط خرید رو بگیر.',
             ['کامنت: درآمد',
              'WELCOME10 • ۱۰٪ تا ۱۵۰٬۰۰۰ تومان',
              'حداقل خرید: ۱۰۰٬۰۰۰ تومان',
              '۴ قسط ترب\u200cپی / دیجی\u200cپی؛ طبق شرایط درگاه'])],
  'primary_product_id': 'canva-pro'},
 {'idea_id': 'IG10_08',
  'segment': 'price_shock_dollar_tax_vs_kelidbox_installments',
  'keyword': 'قیمت',
  'title_fa': 'قبل پرداخت، قیمت نهایی و شرایط قسط را ببین',
  'persona_fa': 'هر کسی که قبلاً خواسته ChatGPT یا Canva بخرد و با دردسر ویزاکارت، نرخ دلار، کارمزد و ترس از بلاک '
                'شدن کارت روبه\u200cرو شده.',
  'pain_fa': 'قیمت دلاری + مالیات + کارمزد کارت مجازی + ریسک کلاهبرداری فروشنده\u200cهای تلگرامی '
             'بی\u200cنام\u200cونشان.',
  'trigger': 'ضرر نکردن (loss aversion) + اعتماد (اینماد) + سبک شدن پرداخت با قسط',
  'hook_visual': "A 3D character's wallet screams and runs away as a receipt keeps printing extra lines: '$20', "
                 "'+ مالیات', '+ کارمزد کارت مجازی', '+ نرخ دلار امروز'… The receipt grows longer than the room. "
                 'Show the transformation in the FIRST 3 seconds; do not render text in the generated image.',
  'hook_fa': 'قیمت نهایی چقدر میشه؟',
  'before_fa': 'قبل پرداخت: قیمت نهایی و شرایط پلن نامشخص؛ هیچ مقایسه دلاری یا مالیاتی بدون فاکتور همسان منتشر '
               'نشود.',
  'after_fa': 'قیمت تومانی پلن منتخب، سقف تخفیف و برنامه اقساط را در تسویه بررسی کن؛ تحویل مطابق زمان صفحه محصول.',
  'products': ['chatgpt-plus', 'draft_0794ef61-67db-4aa0-9cd6-0977addacf48', 'canva-pro'],
  'shots': [(8,
             "A 3D character's wallet screams and runs away as a receipt keeps printing extra lines: '$20', '+ "
             "مالیات', '+ کارمزد کارت مجازی', '+ نرخ دلار امروز'… The receipt grows longer than the room. Show "
             'the transformation in the FIRST 3 seconds; do not render text in the generated image.',
             '0–3s: reveal the hook immediately. Say in Persian (Farsi): "قیمت نهایی چقدر میشه؟". 3–8s: hold on '
             'the result; no extra dialogue.',
             'قیمت نهایی چقدر میشه؟',
             ['قیمت نهایی چقدر میشه؟']),
            (8,
             '3D Pixar-style animation, soft cinematic lighting, vertical 9:16, warm Iranian everyday setting, '
             'expressive faces, shallow depth of field. The same man in a dark alley-like Telegram chat world '
             "talking to a shady hooded seller with no name; a 'Blocked' stamp hits his virtual card.",
             'Spooky lighting, the seller vanishes in smoke. Character says in Persian (Farsi): "ویزاکارت هم بلاک '
             'شد، فروشنده تلگرامی هم غیب شد!"',
             'ویزاکارت هم بلاک شد، فروشنده تلگرامی هم غیب شد!',
             ['کارت مجازی بلاک ❌', 'فروشنده ناشناس 👻']),
            (8,
             '3D Pixar-style animation, soft cinematic lighting, vertical 9:16, warm Iranian everyday setting, '
             'expressive faces, shallow depth of field. A bright clean shop interior: a friendly 3D KelidBox '
             "mascot shows a big screen with the product's Toman price, the Enamad trust seal glowing, and a "
             "button '۴ قسط طبق شرایط درگاه'.",
             'Mascot taps the screen; the long receipt shrinks into four small equal coins. Mascot says in '
             'Persian (Farsi): "تو کلیدباکس قیمت تومانیه، با نماد اینماد، و می\u200cتونی چهار قسطه بدی."',
             'تو کلیدباکس قیمت تومانیه، با نماد اینماد، و می\u200cتونی چهار قسطه بدی.',
             ['قیمت تومانی شفاف ✅', 'نماد اینماد 🛡️', '۴ قسط طبق شرایط درگاه 💳']),
            (8,
             'Vertical 9:16. Real checkout screen recording added in editing: chosen plan, WELCOME10 field and '
             'final total. No synthetic successful order.',
             'Pause on terms. Say in Persian: "تخفیف سقف داره؛ مبلغ نهایی و شرایط قسط رو چک کن."',
             'تخفیف سقف داره؛ مبلغ نهایی و شرایط قسط رو چک کن.',
             ['۱۰٪ تا سقف ۱۵۰٬۰۰۰ تومان', 'حداقل خرید ۱۰۰٬۰۰۰ تومان']),
            (8,
             'Vertical 9:16, same character and setting. Hold a clean phone mockup with empty space for a REAL '
             'product screenshot added in editing. Do not generate logos, checkout UI, seals or readable text.',
             'Slow push-in. Say in Persian (Farsi): "«قیمت» رو کامنت کن؛ لینک و شرایط خرید رو بگیر.". Leave space '
             'for RTL overlays.',
             '«قیمت» رو کامنت کن؛ لینک و شرایط خرید رو بگیر.',
             ['کامنت: قیمت',
              'WELCOME10 • ۱۰٪ تا ۱۵۰٬۰۰۰ تومان',
              'حداقل خرید: ۱۰۰٬۰۰۰ تومان',
              '۴ قسط ترب\u200cپی / دیجی\u200cپی؛ طبق شرایط درگاه'])],
  'primary_product_id': 'canva-pro'},
 {'idea_id': 'IG10_09',
  'segment': 'families_and_commuters_ad_free_entertainment',
  'keyword': 'بدون تبلیغ',
  'title_fa': 'برای تماشای یوتیوب، گزینه بدون تبلیغ را بشناس',
  'persona_fa': 'پدر و مادرهایی که برای بچه کارتون یوتیوب می\u200cگذارند، کارمندهای توی مترو و تاکسی، و '
                'خانواده\u200cهایی که آخر هفته فیلم می\u200cبینند.',
  'pain_fa': 'تبلیغ وسط تماشای ویدیو؛ انتخاب پلن مناسب بدون اشتباه گرفتن قابلیت سرویس\u200cها.',
  'trigger': 'کمدی خانوادگی آشنا (relatable) + آرامش خانه',
  'hook_visual': "A 3D toddler watching a cartoon on a tablet; an ad pops up, the toddler's face turns red and he "
                 "transforms into a tiny screaming volcano while the dad dives across the room to hit 'Skip'. "
                 'Show the transformation in the FIRST 3 seconds; do not render text in the generated image.',
  'hook_fa': 'باز وسط کارتون تبلیغ؟',
  'before_fa': 'تبلیغات میان ویدیوهای یوتیوب؛ قابلیت\u200cها و محدودیت\u200cهای هر سرویس را جداگانه بررسی کن.',
  'after_fa': 'کارتون بی\u200cوقفه و دانلود آفلاین برای سفر، موزیک پس\u200cزمینه در مترو، شب فیلم خانوادگی با '
              'Netflix و Disney+ 4K.',
  'products': ['youtube-premium', 'spotify-premium', 'netflix-4k', 'draft_7aa99417-2013-4c23-b0de-b1075feb7fa1'],
  'shots': [(8,
             "A 3D toddler watching a cartoon on a tablet; an ad pops up, the toddler's face turns red and he "
             "transforms into a tiny screaming volcano while the dad dives across the room to hit 'Skip'. Show "
             'the transformation in the FIRST 3 seconds; do not render text in the generated image.',
             '0–3s: reveal the hook immediately. Say in Persian (Farsi): "باز وسط کارتون تبلیغ؟". 3–8s: hold on '
             'the result; no extra dialogue.',
             'باز وسط کارتون تبلیغ؟',
             ['باز وسط کارتون تبلیغ؟']),
            (8,
             'Vertical 9:16. Adult commuter watching an ordinary YouTube video; an ad interrupts. Not a Spotify '
             'lock-screen example.',
             'Commuter pauses. Say in Persian: "وسط آموزش، دوباره تبلیغ اومد."',
             'وسط آموزش، دوباره تبلیغ اومد.',
             ['وقفه وسط آموزش']),
            (8,
             '3D Pixar-style animation, soft cinematic lighting, vertical 9:16, warm Iranian everyday setting, '
             "expressive faces, shallow depth of field. Magical transition: a glowing 'Premium' key turns in the "
             'tablet; the toddler watches a cartoon peacefully with no ads, then the same cartoon downloaded '
             'offline in a car on a road trip.',
             'Golden key turns, ads shatter like glass, calm music. Narrator says in Persian (Farsi): "با یوتیوب '
             'پریمیوم: بدون تبلیغ، پخش در پس\u200cزمینه، دانلود برای سفر."',
             'با YouTube Premium: بدون تبلیغ، پخش در پس\u200cزمینه، دانلود برای سفر.',
             ['بدون تبلیغ ✅', 'دانلود آفلاین برای سفر 🚗']),
            (8,
             'Vertical 9:16. Family selects a viewing service after reading plan and device limits; no guaranteed '
             '4K on every device.',
             'Warm family scene. Say in Persian: "کیفیت و دانلود به سرویس، دستگاه و پلن بستگی داره."',
             'کیفیت و دانلود به سرویس، دستگاه و پلن بستگی داره.',
             ['شرایط پلن را بخوان']),
            (8,
             'Vertical 9:16, same character and setting. Hold a clean phone mockup with empty space for a REAL '
             'product screenshot added in editing. Do not generate logos, checkout UI, seals or readable text.',
             'Slow push-in. Say in Persian (Farsi): "«بدون تبلیغ» رو کامنت کن؛ لینک و شرایط خرید رو بگیر.". Leave '
             'space for RTL overlays.',
             '«بدون تبلیغ» رو کامنت کن؛ لینک و شرایط خرید رو بگیر.',
             ['کامنت: بدون تبلیغ',
              'WELCOME10 • ۱۰٪ تا ۱۵۰٬۰۰۰ تومان',
              'حداقل خرید: ۱۰۰٬۰۰۰ تومان',
              '۴ قسط ترب\u200cپی / دیجی\u200cپی؛ طبق شرایط درگاه'])],
  'primary_product_id': 'youtube-premium'},
 {'idea_id': 'IG10_10',
  'segment': 'gamers_and_gen_z_safe_installments',
  'keyword': 'گیم',
  'title_fa': 'برای خرید شارژ بازی، نسخه و ریجن را تطبیق بده',
  'persona_fa': 'گیمر بزرگسال؛ برای کاربران زیر سن قانونی، خرید و تصمیم اعتباری فقط توسط والد یا سرپرست.',
  'pain_fa': 'کلاهبرداری فروشنده\u200cهای ناشناس، شارژ نشدن، پول کافی برای اسکین/بازی جدید نداشتن، لگ و پینگ '
             'بالا.',
  'trigger': 'هویت گیمری + ترس از کلاهبرداری + «الان می\u200cتونم بخرم» با قسط',
  'hook_visual': 'A 3D teen gamer about to buy CP from a shady hooded figure in a neon alley; a giant cartoon hat '
                 '(کلاه) slowly lowers onto his head from the sky — he freezes. Show the transformation in the '
                 'FIRST 3 seconds; do not render text in the generated image.',
  'hook_fa': 'قبل خرید، ریجن رو چک کن!',
  'before_fa': 'پیام فروشنده تلگرامی: «اول کارت به کارت کن، بعد شارژ می\u200cکنم» → بلاک شدن و پول از دست رفته.',
  'after_fa': 'نسخه Global و روش شارژ Activision را برای CP تطبیق بده؛ قیمت، زمان تحویل و شرایط اعتبار را قبل '
              'پرداخت بخوان.',
  'products': ['cod-mobile-cp',
               'roblox-robux',
               'valorant-points',
               'telegram-stars',
               'steam-gift-card',
               'draft_551f9b12-deb2-45dd-a9db-322719caa601'],
  'shots': [(8,
             'A 3D teen gamer about to buy CP from a shady hooded figure in a neon alley; a giant cartoon hat '
             '(کلاه) slowly lowers onto his head from the sky — he freezes. Show the transformation in the FIRST '
             '3 seconds; do not render text in the generated image.',
             '0–3s: reveal the hook immediately. Say in Persian (Farsi): "قبل خرید، ریجن رو چک کن!". 3–8s: hold '
             'on the result; no extra dialogue.',
             'قبل خرید، ریجن رو چک کن!',
             ['قبل خرید، ریجن رو چک کن!']),
            (8,
             '3D Pixar-style animation, soft cinematic lighting, vertical 9:16, warm Iranian everyday setting, '
             'expressive faces, shallow depth of field. The gamer in his room staring at a Valorant skin store '
             'and a Steam game page; his piggy bank is cracked and nearly empty; ping meter shows 180ms in red.',
             'Piggy bank coughs a single coin, ping meter blinks red. Gamer says in Persian (Farsi): "پولم هم به '
             'اسکین جدید نمی\u200cرسه، پینگمم صد و هشتاده!"',
             'پولم هم به اسکین جدید نمی\u200cرسه، پینگم هم صد و هشتاده!',
             ['پول نمی\u200cرسه 💸', 'پینگ ۱۸۰ 🐢']),
            (8,
             'Vertical 9:16. Adult gamer and parent inspect a real product page for Global COD Mobile CP; no '
             'fabricated trust badge.',
             'Focus on region label. Say in Persian: "نسخه و ریجن رو تطبیق بده؛ بعد شرایط خرید رو بخون."',
             'نسخه و ریجن رو تطبیق بده؛ بعد شرایط خرید رو بخون.',
             ['نسخه Global و حساب سازگار', 'قسط فقط طبق شرایط اعتبار']),
            (8,
             'Vertical 9:16. Adult gamer checks item details before buying. No ping meter, victory or performance '
             'claim.',
             'Calm comparison shot. Say in Persian: "خرید آیتم، برد یا پینگ بهتر رو تضمین نمی\u200cکنه."',
             'خرید آیتم، برد یا پینگ بهتر رو تضمین نمی\u200cکنه.',
             ['بدون تضمین برد یا پینگ']),
            (8,
             'Vertical 9:16, same character and setting. Hold a clean phone mockup with empty space for a REAL '
             'product screenshot added in editing. Do not generate logos, checkout UI, seals or readable text.',
             'Slow push-in. Say in Persian (Farsi): "«گیم» رو کامنت کن؛ لینک و شرایط خرید رو بگیر.". Leave space '
             'for RTL overlays.',
             '«گیم» رو کامنت کن؛ لینک و شرایط خرید رو بگیر.',
             ['کامنت: گیم',
              'WELCOME10 • ۱۰٪ تا ۱۵۰٬۰۰۰ تومان',
              'حداقل خرید: ۱۰۰٬۰۰۰ تومان',
              '۴ قسط ترب\u200cپی / دیجی\u200cپی؛ طبق شرایط درگاه'])],
  'primary_product_id': 'cod-mobile-cp'}]
