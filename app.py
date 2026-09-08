import streamlit as st
import asyncio
import pandas as pd
from scrapers.google import GoogleScraper
from core.db import DatabaseManager

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

# Sidebar for History
with st.sidebar:
    st.header("🗄️ سجل العقارات")
    if st.button("عرض كل العقارات المحفوظة", use_container_width=True):
        st.session_state['show_history'] = True
    if st.button("بحث جديد", use_container_width=True):
        st.session_state['show_history'] = False

if st.session_state.get('show_history', False):
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
else:
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
        max_pages = st.number_input("عدد الصفحات (1-10)", min_value=1, max_value=10, value=5)

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
            scraper_api_key = "06ede5861ed79f12ad4ed6f275ce0038"
            google_scraper = GoogleScraper(scraper_api_key)
            return await google_scraper.search(final_query, time_filter, max_pages=max_pages)
            
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
