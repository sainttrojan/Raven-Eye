import streamlit as st
import asyncio
import pandas as pd
from scrapers.google import GoogleScraper
from scrapers.dubizzle import DubizzleScraper
from core.db import DatabaseManager
from core.config import load_api_keys, save_api_keys
from core.broker_osint import (
    extract_contacts,
    extract_profile_link,
    extra_summary,
    guess_usernames_from_email,
    is_available as osint_available,
    scan_email as osint_scan_email,
    scan_username as osint_scan_username,
)
from core.phone_osint import full_check as phone_full_check
from core.phone_osint import find_in_database as phone_find_in_db
from core.phone_osint import web_footprint as phone_web_footprint
from core.phone_osint import web_footprint_sites as phone_web_footprint_sites
from core.deep_investigate import investigate as deep_investigate

st.set_page_config(page_title="Raven Eye System", page_icon="🏢", layout="wide")

st.markdown("""
    <style>
        body, .stApp {
            direction: rtl;
            text-align: right;
        }
        .stTextInput>div>div>input {
            font-size: 16px !important;
            padding: 12px !important;
            border-radius: 6px !important;
        }
        .stButton>button, .stDownloadButton>button {
            border-radius: 6px !important;
            font-size: 16px !important;
            font-weight: 500 !important;
            padding: 8px 24px !important;
            transition: all 0.2s ease-in-out;
            margin-top: 28px;
        }
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {
            padding-top: 2rem;
            max-width: 1000px;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize Database
db = DatabaseManager()
if "api_keys" not in st.session_state:
    st.session_state["api_keys"] = load_api_keys()

# Default API Key in session state
if 'scraper_api_key' not in st.session_state:
    st.session_state['scraper_api_key'] = ""

from core.config import load_zenrows_key, save_zenrows_key
if 'zenrows_key' not in st.session_state:
    st.session_state['zenrows_key'] = load_zenrows_key()

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["البحث المباشر", "العقارات المحفوظة", "الإعدادات", "التحقيق في المعلن", "تحقيق برقم الموبايل", "تحقيق شامل", "واتساب سندر"])

with tab3:
    st.subheader("إعدادات النظام (API Keys)")

    st.markdown("#### 🔑 ZenRows API Key (محرك السحب الأساسي)")
    st.caption("ZenRows هو المحرك الأساسي للسحب من Dubizzle وجوجل — بيتخطى Cloudflare تلقائياً.")
    zenrows_input = st.text_input("ZenRows API Key:", value=st.session_state['zenrows_key'], type="password")
    if st.button("حفظ ZenRows Key"):
        if zenrows_input.strip():
            st.session_state['zenrows_key'] = zenrows_input.strip()
            save_zenrows_key(zenrows_input.strip())
            st.success("✅ تم حفظ ZenRows Key!")
        else:
            st.error("ادخل الـ Key الأول.")

    st.divider()
    st.markdown("#### 🔑 ScraperAPI Keys (للبصمة الرقمية على جوجل فقط)")
    st.caption("مش مطلوبة للسحب الأساسي — بس لو عايز ميزة 'بصمة الويب' لأرقام الموبايل.")
    keys_text = st.text_area("مفاتيح ScraperAPI (مفتاح واحد في كل سطر):", value="\n".join(st.session_state['api_keys']), height=100)
    if st.button("حفظ ScraperAPI Keys"):
        new_keys = [k.strip() for k in keys_text.split('\n') if k.strip()]
        if new_keys:
            st.session_state['api_keys'] = new_keys
            save_api_keys(new_keys)
            st.success("تم تحديث مفاتيح ScraperAPI!")
        else:
            st.error("يجب إدخال مفتاح واحد على الأقل.")

    st.divider()
    st.markdown("#### فيسبوك ماركتبليس (مصدر سوشيال)")
    from core.config import fb_session_available
    if fb_session_available():
        st.success("جلسة فيسبوك موجودة — اختيار 'Facebook فقط' هيسحب مباشر من الماركتبليس.")
    else:
        st.warning("مفيش جلسة فيسبوك محفوظة.")
        st.caption("للتفعيل من التيرمينال مرة واحدة (هيفتح متصفح تسجل فيه الدخول بنفسك، والباسورد مش بيتخزن):")
        st.code("cd ~/Desktop/Raven-Eye && ./venv/bin/python fb_login.py")

    st.divider()
    st.markdown("#### جروبات فيسبوك (عقارات مدينتي)")
    st.caption("روابط الجروبات اللي حسابك عضو فيها — رابط في كل سطر. مثال: https://www.facebook.com/groups/madinatyowners")
    from core.config import load_fb_groups, save_fb_groups
    groups_text = st.text_area("روابط الجروبات:", value="\n".join(load_fb_groups()), height=120)
    if st.button("حفظ الجروبات"):
        new_groups = [g.strip() for g in groups_text.split("\n") if g.strip()]
        save_fb_groups(new_groups)
        st.success(f"تم حفظ {len(new_groups)} جروب.")
    else:
        if load_fb_groups():
            st.caption(f"المسجل حاليا: {len(load_fb_groups())} جروب.")


with tab2:
    st.subheader("العقارات المحفوظة مسبقاً")
    history_data = db.get_all_properties()
    if history_data:
        df_history = pd.DataFrame(history_data)
        st.dataframe(df_history, use_container_width=True)
        
        # Download History
        output_file = 'history_app.xlsx'
        df_history.to_excel(output_file, index=False)
        with open(output_file, "rb") as file:
            st.download_button(
                label="تحميل سجل العقارات (Excel)",
                data=file,
                file_name="RavenEye_History.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=False
            )
    else:
        st.info("لا توجد عقارات محفوظة حتى الآن.")

with tab1:
    query = st.text_input("", placeholder="أدخل كلمات البحث...")

    col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.5, 1])

    with col1:
        time_option = st.selectbox("تاريخ النشر", ["أي وقت", "آخر 24 ساعة", "آخر أسبوع", "آخر شهر"])

    with col2:
        site_option = st.selectbox("الموقع", [
            "جميع المواقع", 
            "PropertyFinder فقط", 
            "Dubizzle فقط", 
            "Aqarmap فقط",
            "Facebook فقط",
            "جروبات فيسبوك",
            "Instagram فقط",
            "Twitter فقط"
        ])

    with col3:
        st.write("")
        st.write("")
        exact_match = st.checkbox("تطابق الجملة بالكامل", value=False)

    with col4:
        st.write("")
        st.write("")
        max_pages = st.number_input("عدد الصفحات", min_value=1, max_value=200, value=5)

    colf1, colf2 = st.columns(2)
    with colf1:
        madinaty_only = st.checkbox("مدينتي فقط (يستبعد الشروق/بدر/الرحاب/التجمع...)", value=True)
    with colf2:
        owner_filter = st.selectbox("المعلن", ["الكل", "مالك فقط", "بروكر فقط", "غير معروف فقط"])

    fb_details = False
    fb_detail_limit = 10
    fb_groups: list = []
    if site_option == "Facebook فقط":
        from core.config import fb_session_available
        if fb_session_available():
            st.success("جلسة فيسبوك موجودة — السحب هيكون مباشر من الماركتبليس.")
        else:
            st.warning("مفيش جلسة فيسبوك — هيتم السحب عبر جوجل كبديل. للتفعيل: venv/bin/python fb_login.py")
        fb_details = st.checkbox("فتح صفحات الإعلانات لجلب الوصف ورقم الهاتف (أبطأ)", value=False)
        if fb_details:
            fb_detail_limit = st.number_input("عدد الإعلانات للتفصيل", min_value=1, max_value=30, value=10)

    if site_option == "جروبات فيسبوك":
        from core.config import fb_session_available, load_fb_groups
        fb_groups = load_fb_groups()
        if fb_session_available() and fb_groups:
            st.success(f"هيتم البحث في {len(fb_groups)} جروب مسجل.")
        elif not fb_session_available():
            st.warning("مفيش جلسة فيسبوك — للتفعيل: venv/bin/python fb_login.py")
        if not fb_groups:
            st.warning("مفيش جروبات متسجلة — ضيف روابط الجروبات من تاب الإعدادات الأول.")
        else:
            st.caption("الجروبات: " + "، ".join(fb_groups[:5]) + ("..." if len(fb_groups) > 5 else ""))

    search_clicked = st.button("بحث", use_container_width=True)

    if search_clicked and query:
        final_query = query
        if exact_match:
            final_query = f'"{query}"'
            
        if site_option == "PropertyFinder فقط":
            final_query += " site:propertyfinder.eg"
        elif site_option == "Dubizzle فقط":
            final_query += " site:dubizzle.com.eg"
        elif site_option == "Aqarmap فقط":
            final_query += " site:aqarmap.com.eg"
        elif site_option == "Facebook فقط":
            final_query += " site:facebook.com"
        elif site_option == "Instagram فقط":
            final_query += " site:instagram.com"
        elif site_option == "Twitter فقط":
            final_query += " (site:twitter.com OR site:x.com)"
            
        time_filter = ""
        if time_option == "آخر 24 ساعة":
            time_filter = "qdr:d"
        elif time_option == "آخر أسبوع":
            time_filter = "qdr:w"
        elif time_option == "آخر شهر":
            time_filter = "qdr:m"

        # Snapshot session values here (main thread): worker threads
        # cannot access st.session_state.
        api_keys = list(st.session_state.get("api_keys") or [])

        async def fetch_results(keys):
            if site_option == "Dubizzle فقط":
                scraper = DubizzleScraper(keys)
                return await scraper.search(query, time_filter, max_pages=max_pages)
            else:
                scraper = GoogleScraper(keys)
                return await scraper.search(final_query, time_filter, max_pages=max_pages)

        def run_in_thread():
            """Run async fetch in a clean thread to avoid Streamlit event loop conflicts."""
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                if site_option == "Facebook فقط":
                    from core.config import fb_session_available
                    from core.fb_session import FacebookNotLoggedIn, run_facebook_search
                    if fb_session_available():
                        try:
                            future = ex.submit(run_facebook_search, query, max_pages,
                                               fb_details, fb_detail_limit)
                            return future.result(timeout=600)
                        except FacebookNotLoggedIn as e:
                            st.warning(f"{e} — هنكمل عبر بحث جوجل كبديل.")
                        except Exception as e:
                            st.warning(f"سحب فيسبوك المباشر فشل ({e}) — هنكمل عبر بحث جوجل كبديل.")
                    else:
                        st.info("هنبحث عبر جوجل: site:facebook.com (الجلسة المباشرة مش متفعلة).")
                if site_option == "جروبات فيسبوك":
                    from core.fb_session import FacebookNotLoggedIn, run_facebook_groups_search
                    try:
                        future = ex.submit(run_facebook_groups_search, query, fb_groups,
                                           min(int(max_pages), 5))
                        return future.result(timeout=900)
                    except FacebookNotLoggedIn as e:
                        st.error(str(e))
                        return []
                    except Exception as e:
                        st.error(f"سحب الجروبات فشل: {e}")
                        return []
                future = ex.submit(asyncio.run, fetch_results(api_keys))
                return future.result(timeout=300)

        with st.spinner(f"جاري سحب البيانات من {max_pages} صفحات... برجاء الانتظار"):
            try:
                results = run_in_thread()

                if results:
                    st.success(f"تم استخراج {len(results)} نتيجة بنجاح.")

                    from core.listing_classifier import is_madinaty, classify
                    from core.phone_osint import find_in_database as _phone_corr

                    data = []
                    new_count = 0
                    skipped_city = 0
                    for result in results:
                        res_dict = result.to_dict()
                        title = res_dict.get('Title', '') or ''
                        desc = res_dict.get('Description', '') or ''
                        url = res_dict.get('URL', '') or ''
                        if madinaty_only:
                            geo = is_madinaty(title, desc, url, strict=True)
                            if not geo["in_madinaty"]:
                                skipped_city += 1
                                continue
                        phone = res_dict.get('Phone Number', '') or ''
                        phone_count = None
                        if phone:
                            try:
                                corr = _phone_corr(phone, db)
                                phone_count = corr.get("count") if corr.get("ok") else None
                            except Exception:
                                phone_count = None
                        cls = classify(title, desc, url,
                                       phone_listing_count=phone_count,
                                       scraper_broker_type=res_dict.get('Broker Type'),
                                       author=res_dict.get('Author', '') or '')
                        if owner_filter == "مالك فقط" and cls["label"] != "owner":
                            continue
                        if owner_filter == "بروكر فقط" and cls["label"] != "broker":
                            continue
                        if owner_filter == "غير معروف فقط" and cls["label"] != "unknown":
                            continue
                        data.append({
                            'العنوان': title,
                            'السعر': res_dict.get('Price', ''),
                            'المساحة': res_dict.get('Area', ''),
                            'رقم الهاتف': phone,
                            'المعلن': cls["label_ar"],
                            'سبب التصنيف': "; ".join(cls["reasons"][:2]),
                            'صاحب البوست': res_dict.get('Author', '') or '',
                            'بروفايل المعلن': res_dict.get('Author URL', '') or '',
                            'الرابط': url,
                            'الوصف': desc
                        })

                        # Save to database
                        inserted = db.insert_property(res_dict)
                        if inserted:
                            new_count += 1
                        try:
                            db.set_classification(url, cls["label"],
                                                  cls["broker_score"], cls["owner_score"])
                        except Exception:
                            pass

                    if madinaty_only and skipped_city:
                        st.info(f"تم استبعاد {skipped_city} نتيجة خارج مدينتي.")
                    st.info(f"تم إضافة {new_count} عقار جديد لقاعدة البيانات.")

                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)

                    output_file = 'results_app.xlsx'
                    df.to_excel(output_file, index=False)

                    with open(output_file, "rb") as file:
                        st.download_button(
                            label="تحميل التقرير (Excel)",
                            data=file,
                            file_name="RavenEye_Report.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=False
                        )
                else:
                    st.warning("لم يتم العثور على بيانات مطابقة.")
            except Exception as e:
                st.error(f"حدث خطأ في النظام: {e}")
                import traceback
                st.code(traceback.format_exc())



with tab4:
    st.subheader("التحقيق في المعلن (user-scanner)")
    st.caption("استخرج الايميلات واليوزرات من نص إعلان، ثم افحص بصمتهم الرقمية عبر user-scanner.")

    if not osint_available():
        st.error("user-scanner غير متاح. ثبته أو حدد المسار في USER_SCANNER_BIN. "
                 "المسار الافتراضي: /home/ahmed/Desktop/user-scanner/.venv/bin/user-scanner")
    else:
        st.success("user-scanner متاح وجاهز.")

    raw_text = st.text_area("الصق نص الإعلان أو الوصف (يستخرج الايميلات واليوزرات تلقائيا)",
                            height=120, placeholder="مثال: شقة من المالك @broker_eg تواصل instagram.com/broker_eg أو mail@example.com")
    listing_url = st.text_input("رابط الإعلان (اختياري، يساعد في استخراج اليوزر)", placeholder="https://...")

    if st.button("استخراج جهات الاتصال"):
        contacts = extract_contacts(raw_text or "", listing_url or "")
        st.write("الايميلات:", contacts["emails"] or "لا يوجد")
        st.write("اليوزرات:", contacts["usernames"] or "لا يوجد")

    st.divider()
    col_os1, col_os2 = st.columns(2)
    with col_os1:
        target_type = st.selectbox("نوع الهدف", ["username", "email"])
    with col_os2:
        target_value = st.text_input("الهدف", placeholder="broker_eg أو mail@example.com")

    modules_value = st.text_input("موديولات محددة (اختياري، أسرع)", value="",
                                  help="سيبها فاضية لفحص شامل (200+ موقع للايميل). حدد موديولات بس لو عايز سرعة. مثال: github,instagram")
    category_value = st.text_input("كاتيجوري محددة (اختياري)", value="", placeholder="مثال: social")

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        allow_loud = st.checkbox("فحص المواقع الحساسة (allow-loud)", value=False,
                                 help="يشمل مواقع بتشتغل عبر password-reset وقد تنبه صاحب الحساب. يزود عدد النتايج.")
    with col_opt2:
        cross_scan = st.checkbox("تتبع الروابط المسربة (cross-scan)", value=False,
                                 help="بعد الفحص، يتتبع الهاندلز واللينكات المكتشفة ويفحصها كأهداف جديدة.")

    if st.button("بدء فحص المعلن", use_container_width=True):
        if not target_value.strip():
            st.error("ادخل اليوزرنيم أو الايميل الأول.")
        else:
            mods = modules_value.strip() or None
            cat = category_value.strip() or None
            with st.spinner("جاري فحص البصمة الرقمية... قد يستغرق دقائق للفحص الشامل"):
                try:
                    if target_type == "email":
                        res = osint_scan_email(target_value.strip(), modules=mods, category=cat, timeout=600,
                                               allow_loud=allow_loud, cross_scan=cross_scan)
                    else:
                        res = osint_scan_username(target_value.strip(), modules=mods, category=cat, timeout=600,
                                                  allow_loud=allow_loud, cross_scan=cross_scan)
                except Exception as e:
                    st.error(f"فشل الفحص: {e}")
                    res = None
            if res:
                if not res.get("ok"):
                    st.error(f"فشل الفحص: {res.get('error')}")
                else:
                    st.success(f"تم الفحص: {res['total_hits']} نتيجة مؤكدة من {res['total_checked']} موقع.")
                    st.caption("ملحوظة: سكان الايميل يثبت التسجيل فقط، ورابطه هو صفحة الموقع الرئيسية — البروفايل الحقيقي ييجي من سكان اليوزرنيم.")
                    try:
                        db.save_osint_result(res.get("type", target_type), res["target"],
                                             res["total_hits"], res["total_checked"],
                                             res["hits"], listing_url or "")
                    except Exception:
                        pass
                    if res["hits"]:
                        df_os = pd.DataFrame([{
                            "الموقع": h.get("site_name", ""),
                            "الكاتيجوري": h.get("category", ""),
                            "الحالة": h.get("status", ""),
                            "الرابط": h.get("url", ""),
                            "البروفايل": extract_profile_link(h),
                            "تفاصيل": extra_summary(h),
                        } for h in res["hits"]])
                        st.dataframe(df_os, use_container_width=True)
                    else:
                        st.info("لا توجد حسابات مؤكدة لهذا الهدف في النطاق المختار. جرب تفعيل allow-loud أو امسح الموديولات لفحص شامل.")

                    if target_type == "email":
                        guesses = guess_usernames_from_email(target_value.strip())
                        if guesses:
                            st.divider()
                            st.subheader("خطوة تانية: هات لينكات البروفايل من الايميل")
                            st.caption("الايميل نفسه مش بيدي لينك بروفايل، لكن اليوزرات المستنتجة منه بتعمل كده. اختار واحد وافحصه كيوزرنيم.")
                            guess_choice = st.selectbox("يوزر مستنتج من الايميل", guesses)
                            if st.button("افحص اليوزر المستنتج (يجيب لينكات بروفايل حقيقية)"):
                                with st.spinner("جاري فحص اليوزرنيم..."):
                                    try:
                                        ures = osint_scan_username(guess_choice.strip(), modules=None,
                                                                   category=None, timeout=600,
                                                                   allow_loud=allow_loud)
                                    except Exception as e:
                                        st.error(f"فشل الفحص: {e}")
                                        ures = None
                                if ures and ures.get("ok"):
                                    st.success(f"اليوزر {guess_choice}: {ures['total_hits']} بروفايل مؤكد.")
                                    try:
                                        db.save_osint_result("username", ures["target"],
                                                             ures["total_hits"], ures["total_checked"],
                                                             ures["hits"], listing_url or "")
                                    except Exception:
                                        pass
                                    if ures["hits"]:
                                        df_u = pd.DataFrame([{
                                            "الموقع": h.get("site_name", ""),
                                            "لينك البروفايل": extract_profile_link(h),
                                            "تفاصيل": extra_summary(h),
                                        } for h in ures["hits"]])
                                        st.dataframe(df_u, use_container_width=True)
                                elif ures:
                                    st.error(f"فشل الفحص: {ures.get('error')}")

    st.divider()
    st.subheader("نتائج تحقيقات سابقة")
    try:
        past = db.get_osint_results(limit=50)
    except Exception:
        past = []
    if past:
        df_past = pd.DataFrame([{
            "الهدف": p["target"],
            "النوع": p["target_type"],
            "مؤكدة": p["total_hits"],
            "مفحوصة": p["total_checked"],
            "التاريخ": p["created_at"],
        } for p in past])
        st.dataframe(df_past, use_container_width=True)
    else:
        st.info("لا توجد تحقيقات محفوظة بعد.")

with tab5:
    st.subheader("تحقيق برقم الموبايل (phonenumbers + ignorant)")
    st.caption("تحليل فوري للرقم (الشركة/الصلاحية) + فحص هل هو مسجل على amazon و instagram و snapchat.")

    phone_input = st.text_input("رقم الموبايل", placeholder="01xxxxxxxxx أو +201xxxxxxxxx")
    phone_url = st.text_input("رابط الإعلان المرتبط (اختياري)", placeholder="https://...")
    with_accounts = st.checkbox("فحص الحسابات المرتبطة (ignorant + فيسبوك) — قد يستغرق ~30 ثانية", value=True)
    with_web = st.checkbox("بصمة الويب: دور على الرقم في جوجل (يستهلك من رصيد ScraperAPI)", value=True)
    with_web_sites = st.checkbox("بصمة لكل موقع: فيسبوك/دوبيزل/أولكس... (5 عمليات بحث)", value=False)

    if st.button("افحص الرقم", use_container_width=True):
        if not phone_input.strip():
            st.error("ادخل الرقم الأول.")
        else:
            with st.spinner("جاري فحص الرقم..."):
                try:
                    pres = phone_full_check(phone_input.strip(), with_accounts=with_accounts, timeout=15)
                except Exception as e:
                    st.error(f"فشل الفحص: {e}")
                    pres = None
            if pres:
                if not pres.get("ok"):
                    st.error(pres.get("error", "رقم غير صالح"))
                else:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("الصيغة الدولية", pres["e164"])
                    c2.metric("الشركة", pres.get("carrier", "؟"))
                    c3.metric("صالح", "نعم" if pres.get("valid") else "لا")
                    c4.metric("النوع", pres.get("number_type", "؟"))
                    try:
                        db.save_phone_osint(pres["e164"], pres.get("carrier", ""),
                                            bool(pres.get("valid")), pres.get("accounts", []),
                                            phone_url or "")
                    except Exception:
                        pass
                    accs = pres.get("accounts", [])
                    if pres.get("accounts_error"):
                        st.warning(f"فحص الحسابات لم يكتمل: {pres['accounts_error']}")
                    if accs:
                        df_ph = pd.DataFrame([{
                            "الموقع": a.get("domain", ""),
                            "مسجل": "نعم" if a.get("exists") else "لا",
                            "Rate limit": "نعم" if a.get("rate_limited") else "لا",
                        } for a in accs])
                        st.dataframe(df_ph, use_container_width=True)
                        st.caption("ملحوظة: نتيجة instagram مؤشر وليست قطعية — الـ API بتاعهم أحيانا يرد بتحدي أمني بيتسجل كـ Positive.")
                    elif with_accounts:
                        st.info("لا توجد حسابات مؤكدة أو المواقع ردت بـ rate limit — جرب لاحقا أو غير الـ IP.")

                    st.divider()
                    st.subheader("الرقم ده ظهر عندنا قبل كده؟ (قاعدة بيانات الرادار)")
                    try:
                        corr = phone_find_in_db(phone_input.strip(), db)
                    except Exception as e:
                        corr = {"ok": False, "error": str(e)}
                    if corr.get("ok"):
                        if corr["count"] == 0:
                            st.info("الرقم ده مش موجود في أي إعلان محفوظ عندنا — غالبا معلن جديد.")
                        else:
                            st.warning(f"الرقم ده ظهر في {corr['count']} إعلان محفوظ — راجع لو سمسار بيكرر إعلاناته.")
                            if corr.get("sources"):
                                st.write("المصادر:", "، ".join(f"{k} ({v})" for k, v in corr["sources"].items()))
                            df_corr = pd.DataFrame([{
                                "العنوان": li.get("Title", ""),
                                "المصدر": li.get("Source", ""),
                                "السعر": li.get("Price", ""),
                                "النوع": li.get("Broker Type", ""),
                                "الرابط": li.get("URL", ""),
                            } for li in corr["listings"][:15]])
                            st.dataframe(df_corr, use_container_width=True)
                    else:
                        st.error(corr.get("error", "تعذر البحث الداخلي"))

                    if with_web:
                        st.divider()
                        st.subheader("الرقم ظاهر فين على الويب؟")
                        with st.spinner("جاري البحث في جوجل عن الرقم..."):
                            try:
                                wres = phone_web_footprint(phone_input.strip(),
                                                           st.session_state.get("api_keys", []),
                                                           max_pages=2)
                            except Exception as e:
                                wres = {"ok": False, "error": str(e)}
                        if wres.get("ok"):
                            if wres["count"] == 0:
                                st.info("مفيش ظهور علني مفهرس للرقم ده.")
                            else:
                                st.success(f"لقيت {wres['count']} نتيجة فيها الرقم.")
                                df_w = pd.DataFrame([{
                                    "العنوان": it.get("Title", ""),
                                    "المصدر": it.get("Source", ""),
                                    "الرابط": it.get("URL", ""),
                                } for it in wres["items"][:15]])
                                st.dataframe(df_w, use_container_width=True)
                        else:
                            st.warning(wres.get("error", "تعذر البحث"))

                    if with_web_sites:
                        st.divider()
                        st.subheader("الرقم مذكور فين؟ (لكل موقع)")
                        with st.spinner("جاري البحث في كل موقع..."):
                            try:
                                sres = phone_web_footprint_sites(
                                    phone_input.strip(),
                                    st.session_state.get("api_keys", []))
                            except Exception as e:
                                sres = {"ok": False, "error": str(e)}
                        if sres.get("ok"):
                            rows = []
                            for site, sd in sres["sites"].items():
                                if sd.get("error"):
                                    rows.append({"الموقع": site, "الظهور": "خطأ",
                                                 "مثال": sd["error"]})
                                elif sd["count"]:
                                    first = sd["items"][0]
                                    rows.append({"الموقع": site,
                                                 "الظهور": f"{sd['count']} نتيجة",
                                                 "مثال": first.get("Title", "")})
                                else:
                                    rows.append({"الموقع": site, "الظهور": "لا يوجد",
                                                 "مثال": ""})
                            st.dataframe(pd.DataFrame(rows), use_container_width=True)
                        else:
                            st.warning(sres.get("error", "تعذر البحث"))

                    links = pres.get("links", {})
                    if links:
                        st.divider()
                        st.subheader("لينكات تحقيق يدوي")
                        for label, url in links.items():
                            st.markdown(f"- [{label}]({url})")

    st.divider()
    st.subheader("فحوصات أرقام سابقة")
    try:
        past_ph = db.get_phone_osint(limit=50)
    except Exception:
        past_ph = []
    if past_ph:
        df_past_ph = pd.DataFrame([{
            "الرقم": p["phone"],
            "الشركة": p["carrier"],
            "صالح": "نعم" if p["valid"] else "لا",
            "حسابات مؤكدة": sum(1 for a in p["accounts"] if a.get("exists")),
            "التاريخ": p["created_at"],
        } for p in past_ph])
        st.dataframe(df_past_ph, use_container_width=True)
    else:
        st.info("لا توجد فحوصات أرقام محفوظة بعد.")

with tab6:
    st.subheader("تحقيق شامل: كل المعرفات × كل المواقع")
    st.caption("يشغل كل المحركات مع بعض: الموبايل (تحليل + ignorant + ربط داخلي) و الايميل (كل ~200 موقع) و اليوزرنيم (كل ~880 موقع + المستنتج من الايميل).")
    st.warning("الفحص الشامل بطيء (5-15 دقيقة). سيب المتصفح مفتوح ومتقفلش التاب.")

    d_phone = st.text_input("رقم الموبايل (اختياري)", placeholder="01xxxxxxxxx", key="deep_phone")
    d_email = st.text_input("الايميل (اختياري)", placeholder="mail@example.com", key="deep_email")
    d_user = st.text_input("اليوزرنيم (اختياري)", placeholder="broker_eg", key="deep_user")

    d_col1, d_col2 = st.columns(2)
    with d_col1:
        d_loud = st.checkbox("فحص المواقع الحساسة (allow-loud)", value=False, key="deep_loud")
    with d_col2:
        d_cross = st.checkbox("تتبع الروابط المسربة (cross-scan)", value=False, key="deep_cross")

    if st.button("ابدأ التحقيق الشامل", use_container_width=True):
        if not (d_phone.strip() or d_email.strip() or d_user.strip()):
            st.error("ادخل معرف واحد على الأقل (موبايل أو ايميل أو يوزر).")
        else:
            with st.spinner("تحقيق شامل جارٍ... قد يستغرق دقائق طويلة للفحص الكامل"):
                try:
                    rep = deep_investigate(phone=d_phone.strip(), email=d_email.strip(),
                                           username=d_user.strip(), phone_timeout=20,
                                           scan_timeout=1200, allow_loud=d_loud,
                                           cross_scan=d_cross, db=db)
                except Exception as e:
                    st.error(f"فشل التحقيق: {e}")
                    rep = None
            if rep:
                summ = rep.get("summary", {})
                st.success(f"اكتمل: {summ.get('total_hits', 0)} نتيجة مؤكدة عبر [{', '.join(summ.get('engines', []))}]")

                ph = rep.get("phone")
                if ph:
                    st.divider()
                    st.subheader(f"الموبايل {ph.get('e164', '')}")
                    if not ph.get("ok"):
                        st.error(ph.get("error"))
                    else:
                        st.write(f"الشركة: {ph.get('carrier')} | صالح: {'نعم' if ph.get('valid') else 'لا'}")
                        for a in ph.get("accounts", []):
                            mark = "مسجل" if a.get("exists") else ("rate limit" if a.get("rate_limited") else "غير مسجل")
                            st.write(f"- {a.get('domain')}: {mark}")
                        corr = ph.get("db_correlation", {})
                        if corr.get("ok") and corr.get("count"):
                            st.warning(f"ظهر في {corr['count']} إعلان محفوظ عندنا.")

                em = rep.get("email")
                if em:
                    st.divider()
                    st.subheader(f"الايميل {em.get('target', '')} — كل مواقع الايميل")
                    if not em.get("ok"):
                        st.error(em.get("error"))
                    else:
                        st.write(f"{em.get('total_hits', 0)} موقع مؤكد من {em.get('total_checked', 0)} مفحوص.")
                        if em.get("hits"):
                            st.dataframe(pd.DataFrame([{
                                "الموقع": h.get("site_name", ""),
                                "البروفايل": extract_profile_link(h),
                                "تفاصيل": extra_summary(h),
                            } for h in em["hits"]]), use_container_width=True)

                for ur in rep.get("usernames", []):
                    st.divider()
                    st.subheader(f"اليوزر {ur.get('target', '')} — كل مواقع اليوزرنيم")
                    if not ur.get("ok"):
                        st.error(ur.get("error"))
                    else:
                        st.write(f"{ur.get('total_hits', 0)} بروفايل مؤكد من {ur.get('total_checked', 0)} مفحوص.")
                        if ur.get("hits"):
                            st.dataframe(pd.DataFrame([{
                                "الموقع": h.get("site_name", ""),
                                "لينك البروفايل": extract_profile_link(h),
                                "تفاصيل": extra_summary(h),
                            } for h in ur["hits"]]), use_container_width=True)

with tab7:
    st.subheader("واتساب سندر (من رقمك الشخصي)")
    st.caption("إرسال عبر WhatsApp Web بجلسة موبايلك — نفس فكرة جلسة فيسبوك.")
    st.warning("تنبيه: الإرسال الآلي مخالف لشروط واتساب وقد يعرض الرقم للحظر. أرسل لقوايم موافقة وبفواصل زمنية.")

    from core.wa_sender import (
        build_send_url,
        extract_numbers_from_frame as wa_numbers_from_frame,
        load_subscribers as wa_load_subs,
        parse_targets as wa_parse_targets,
        render_listing as wa_render_listing,
        save_subscribers as wa_save_subs,
        send_messages as wa_send,
        wa_session_available,
    )

    if wa_session_available():
        st.success("جلسة واتساب موجودة.")
    else:
        st.warning("مفيش جلسة واتساب. من التيرمينال مرة واحدة:")
        st.code("cd ~/Desktop/Raven-Eye && ./venv/bin/python wa_login.py")

    subs = wa_load_subs()
    st.caption(f"المشتركين المحفوظين: {len(subs)}")
    use_subs = st.checkbox("إرسال للمشتركين المحفوظين", value=bool(subs))
    extra_numbers = st.text_area("أرقام إضافية (أي صيغة مصرية، رقم في كل سطر)",
                                 height=80, placeholder="01001234567")
    wa_sheet = st.file_uploader("أو ارفع شيت بالأرقام (Excel/CSV — الأرقام تتسحب من كل الخلايا)",
                                type=["xlsx", "xls", "csv"])
    sheet_numbers: list = []
    if wa_sheet is not None:
        try:
            import pandas as pd
            if wa_sheet.name.lower().endswith(".csv"):
                _df = pd.read_csv(wa_sheet, dtype=str, keep_default_na=False)
            else:
                _df = pd.read_excel(wa_sheet, dtype=str)
            sheet_numbers = wa_numbers_from_frame(_df)
            st.success(f"اتلقط {len(sheet_numbers)} رقم من الشيت.")
        except Exception as e:
            st.error(f"تعذر قراءة الشيت: {e}")
    wa_text = st.text_area("نص الرسالة", height=120,
                           placeholder="شقة 120م مدينتي B7 من المالك - 5 مليون...")
    wa_image = st.file_uploader("صورة مرفقة (اختياري)", type=["jpg", "jpeg", "png"])
    wa_delay = st.slider("فاصل بين الرسائل (ثواني)", 5, 60, 12)
    wa_dry = st.checkbox("وضع تجريبي dry-run (لا يرسل شيئا فعليا)", value=True)

    col_wa1, col_wa2 = st.columns(2)
    with col_wa1:
        if st.button("حفظ الأرقام كمشتركين"):
            new_subs = sorted(set(subs) | set(wa_parse_targets(extra_numbers or ""))
                              | set(sheet_numbers))
            wa_save_subs(new_subs)
            st.success(f"تم حفظ {len(new_subs)} مشترك. حدث الصفحة.")
    with col_wa2:
        do_send = st.button("إرسال واتساب", use_container_width=True)

    if do_send:
        targets = list(subs) if use_subs else []
        targets += wa_parse_targets(extra_numbers or "")
        targets += sheet_numbers
        targets = sorted(set(targets))[:30]
        if not targets:
            st.error("مفيش أرقام صالحة.")
        elif not wa_text.strip() and not wa_image:
            st.error("الرسالة فاضية.")
        else:
            img_path = None
            if wa_image:
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                    tmp.write(wa_image.read())
                    img_path = tmp.name
            with st.spinner(f"جاري الإرسال لـ {len(targets)} رقم... (متقفلش التاب)"):
                try:
                    res = wa_send(targets, wa_text.strip(), img_path,
                                  delay=(max(5, wa_delay - 3), wa_delay + 3),
                                  dry_run=wa_dry)
                except Exception as e:
                    st.error(f"فشل الإرسال: {e}")
                    res = None
            if res:
                if res.get("error"):
                    st.error(res["error"])
                else:
                    mode = "تجريبي (متبعتش حاجة)" if res["dry_run"] else "فعلي"
                    st.success(f"وضع {mode}: نجح {res['sent']} / فشل {res['failed']}")
                    st.dataframe(pd.DataFrame([{
                        "الرقم": r.get("target", ""),
                        "الحالة": "تم" if r.get("ok") else "فشل",
                        "ملاحظة": r.get("error", ""),
                    } for r in res["results"]]), use_container_width=True)
