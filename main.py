import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------
# 페이지 기본 설정
# -----------------------------
st.set_page_config(page_title="인구 퍼짐 보기", layout="wide")

st.title("🌱 우리 동네 인구, 얼마나 퍼져 있을까?")
st.write("읍·면·동 단위로 집계된 '총인구'가 얼마나 넓게 퍼져 있는지 눈으로 확인해보는 아주 간단한 앱이에요.")

# -----------------------------
# 1. 데이터 불러오기
# -----------------------------
# pandas는 .gz로 압축된 csv도 자동으로 알아서 풀어서 읽어줘요.
DATA_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"


@st.cache_data
def load_data(url):
    df = pd.read_csv(url, compression="gzip")
    return df


with st.spinner("데이터를 불러오는 중이에요... 조금만 기다려주세요 ☕"):
    df = load_data(DATA_URL)

st.success(f"데이터 불러오기 완료! 전체 {len(df):,}개 행을 확인했어요.")

# -----------------------------
# 2. 가장 최신 연도만 남기기
# -----------------------------
# '연도' 열에서 가장 큰 값(가장 최근 연도)만 골라내요.
latest_year = df["연도"].max()
df_latest = df[df["연도"] == latest_year].copy()

st.info(f"📅 가장 최신 연도인 **{latest_year}년** 데이터만 사용할게요. (읍·면·동 단위, 총 {len(df_latest):,}곳)")
