import streamlit as st
import asyncio
import pandas as pd
from scrapers.google import GoogleScraper

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

query = st.text_input("", placeholder="أدخل كلمات البحث...")

col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.5, 1])

with col1:
    time_option = st.selectbox("تاريخ النشر", ["أي وقت", "آخر 24 ساعة", "آخر أسبوع", "آخر شهر"])

with col2:
    site_option = st.selectbox("الموقع", ["جميع المواقع", "PropertyFinder فقط", "Dubizzle فقط", "Aqarmap فقط"])

with col3:
    st.write("")
    st.write("")
    exact_match = st.checkbox("تطابق الجملة بالكامل", value=False)

with col4:
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
        return await google_scraper.search(final_query, time_filter)
        
    with st.spinner("جاري معالجة البيانات..."):
        try:
            # Fix for Streamlit asyncio runtime errors
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(fetch_results())
            
            if results:
                st.success(f"تم استخراج {len(results)} نتيجة بنجاح.")
                
                data = []
                for result in results:
                    data.append({
                        'العنوان': result.title,           
                        'الرابط': result.url,             
                        'الوصف': result.description      
                    })
                    
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
