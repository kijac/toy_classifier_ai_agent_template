

import streamlit as st
import traceback
from supervisor_agent import SupervisorAgent
from image_input import get_image_streamlit

def main():
    st.set_page_config(
        page_title="장난감 기부 판별 AI",
        page_icon="🧸",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # 헤더
    st.title("🧸 장난감 기부 판별 AI")
    st.markdown("---")
    st.markdown("### 📸 장난감 이미지를 업로드하면, AI가 기부 가능 여부와 처리 방법을 판별해드립니다.")
    
    # 이미지 업로드
    image = get_image_streamlit()
    
    if image:
        # 이미지 표시
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("#### 📷 업로드된 이미지")
            st.image(image, width=300)
        
        with col2:
            try:
                supervisor = SupervisorAgent()
                with st.spinner("🤖 AI가 이미지를 분석 중입니다..."):
                    result = supervisor.process(image)
                
                st.markdown("#### 🔍 AI 분석 결과")
                
                # 기부 가능 여부를 가장 먼저 표시
                if result["기부 가능 여부"] == "가능":
                    st.success("✅ **기부 가능한 장난감입니다!**")
                else:
                    st.error("❌ **기부가 어려운 장난감입니다**")
                    if result["기부 불가 사유"]:
                        st.warning(f"💡 사유: {result['기부 불가 사유']}")
                
                st.markdown("---")
                
                # 분석 상세 정보를 카드 형태로 표시
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.markdown("#### 🎯 장난감 정보")
                    st.info(f"**종류**: {result['장난감 종류']}")
                    st.info(f"**재료**: {result['재료']}")
                    st.info(f"**건전지**: {result['건전지 여부']}")
                
                with col_b:
                    st.markdown("#### 🔧 상태 및 처리")
                    
                    # 파손 상태에 따른 색상 구분
                    damage = result['파손']
                    if damage == "없음":
                        st.success(f"**파손 상태**: {damage} ✨")
                    elif "심각" in damage:
                        st.error(f"**파손 상태**: {damage} ⚠️")
                    else:
                        st.warning(f"**파손 상태**: {damage} 🔍")
                    
                    # 수리/분해 정보
                    repair_info = result['수리/분해']
                    if "수리 불필요" in repair_info:
                        st.success(f"**처리 방법**: {repair_info} 🎉")
                    elif "수리 가능" in repair_info:
                        st.warning(f"**처리 방법**: {repair_info} 🔧")
                    else:
                        st.info(f"**처리 방법**: {repair_info} ♻️")
                        
            except Exception as e:
                st.error(f"❌ 오류가 발생했습니다: {str(e)}")
                st.code(traceback.format_exc())

if __name__ == "__main__":
    main()