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
    st.session_state['scraper_api_key'] = "06ede5861ed79f12ad4ed6f275ce0038"

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["البحث المباشر", "العقارات المحفوظة", "الإعدادات", "التحقيق في المعلن", "تحقيق برقم الموبايل", "تحقيق شامل"])

with tab3:
    st.subheader("إعدادات النظام (API Keys)")
    keys_text = st.text_area("أدخل مفاتيح ScraperAPI (مفتاح واحد في كل سطر):", value="\n".join(st.session_state['api_keys']), height=150)
    if st.button("حفظ الإعدادات"):
        new_keys = [k.strip() for k in keys_text.split('\n') if k.strip()]
        if new_keys:
            st.session_state['api_keys'] = new_keys
            save_api_keys(new_keys)
            st.success("تم تحديث وحفظ مفاتيح الـ API بنجاح!")
        else:
            st.error("يجب إدخال مفتاح واحد على الأقل.")

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

        async def fetch_results():
            if site_option == "Dubizzle فقط":
                scraper = DubizzleScraper(st.session_state['api_keys'])
                return await scraper.search(query, time_filter, max_pages=max_pages)
            else:
                scraper = GoogleScraper(st.session_state['api_keys'])
                return await scraper.search(final_query, time_filter, max_pages=max_pages)
            
        with st.spinner(f"جاري سحب البيانات من {max_pages} صفحات... برجاء الانتظار"):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(fetch_results())
                
                if results:
                    st.success(f"تم استخراج {len(results)} نتيجة بنجاح.")
                    
                    data = []
                    new_count = 0
                    for result in results:
                        res_dict = result.to_dict()
                        data.append({
                            'العنوان': res_dict['Title'],
                            'السعر': res_dict.get('Price', ''),
                            'المساحة': res_dict.get('Area', ''),
                            'رقم الهاتف': res_dict.get('Phone Number', ''),
                            'الرابط': res_dict['URL'],
                            'الوصف': res_dict['Description']
                        })
                        
                        # Save to database
                        inserted = db.insert_property(res_dict)
                        if inserted:
                            new_count += 1
                            
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
    with_accounts = st.checkbox("فحص الحسابات المرتبطة (ignorant) — قد يستغرق ~20 ثانية", value=True)
    with_web = st.checkbox("بصمة الويب: دور على الرقم في جوجل (يستهلك من رصيد ScraperAPI)", value=True)

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
