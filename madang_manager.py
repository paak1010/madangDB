import streamlit as st
import pymysql
import pandas as pd
from typing import Optional
import time

# --- DB 접속 정보 설정 (Secrets.toml 사용) ---
# Secrets.toml 파일이 반드시 .streamlit/secrets.toml 경로에 있어야 합니다.
DB_CONFIG = {
    # host 값은 secrets.toml에서 읽어온 '211.179.110.120' 공인 IP 주소입니다.
    'host': st.secrets["mysql"]["host"], 
    'user': st.secrets["mysql"]["user"],
    'passwd': st.secrets["mysql"]["passwd"],
    'db': st.secrets["mysql"]["db"],
    'charset': st.secrets["mysql"]["charset"]
}

@st.cache_resource(ttl=3600)  # DB 연결을 캐시하여 성능 최적화
def get_db_connection() -> Optional[pymysql.connections.Connection]:
    """데이터베이스 연결을 설정하고 반환합니다."""
    try:
        # DB 접속 시도
        conn = pymysql.connect(**DB_CONFIG)
        st.success("데이터베이스 연결 성공!", icon="✅")
        return conn
    except Exception as e:
        # Timed out 오류 시 포트 포워딩 또는 공인 IP 문제를 안내
        st.error("데이터베이스 연결 오류 발생! (Timed out 오류 예상)", icon="❌")
        st.error(f"오류 상세: {e}")
        st.warning("1. Secrets.toml의 host 값이 **공인 IP(211.179.110.120)**인지 확인하세요.")
        st.warning("2. **공유기 포트 포워딩** 및 **Windows 방화벽** 설정을 확인해야 합니다.")
        return None

# --- 데이터 조회 함수 ---
def search_user_orders(name: str, conn: pymysql.connections.Connection) -> tuple[pd.DataFrame, Optional[int]]:
    """사용자 이름을 기준으로 주문 내역을 조회하고 custid를 반환합니다."""
    
    orders_df = pd.DataFrame()
    custid = None

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 1. 주문 내역 조회 및 custid 확보 (SQL 인젝션 방지)
            sql_orders = """
            SELECT o.custid, c.name, b.bookname, o.saleprice, o.orderdate 
            FROM Customer c, Orders o, Book b
            WHERE c.name = %s AND c.custid = o.custid AND b.bookid = o.bookid;
            """
            cursor.execute(sql_orders, (name,))
            result = cursor.fetchall()
            
            if result:
                orders_df = pd.DataFrame(result)
                custid = result[0]['custid']
            else:
                # 2. 주문이 없더라도 custid만 조회
                sql_cust = "SELECT custid FROM Customer WHERE name = %s;"
                cursor.execute(sql_cust, (name,))
                cust_result = cursor.fetchone()
                if cust_result:
                    custid = cust_result['custid']
            
            return orders_df, custid
            
    except Exception as e:
        st.error(f"SQL 쿼리 오류 발생: {e}")
        return pd.DataFrame(), None

def get_max_order_id(conn: pymysql.connections.Connection) -> int:
    """현재 주문 중 최대 orderid를 조회합니다."""
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT MAX(orderid) AS max_id FROM Orders;")
            result = cursor.fetchone()
            return (result['max_id'] if result and result['max_id'] is not None else 0)
    except Exception as e:
        st.error(f"주문 ID 조회 오류: {e}")
        return 0

def get_all_books(conn: pymysql.connections.Connection) -> list:
    """모든 도서 목록을 조회합니다."""
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT bookid, bookname FROM Book;")
            result = cursor.fetchall()
            return [f"{row['bookid']},{row['bookname']}" for row in result]
    except Exception as e:
        st.error(f"도서 목록 조회 오류: {e}")
        return []

# ----------------------------------------------------
# Streamlit UI 및 로직
# ----------------------------------------------------

st.set_page_config(page_title="마당서점 관리", layout="wide")
st.title("📚 마당서점 고객 및 거래 관리")
st.markdown("---")

db_conn = get_db_connection()

if db_conn:
    # 도서 목록을 세션 상태에 저장 (캐시된 DB 연결 사용)
    if 'book_list' not in st.session_state:
        st.session_state.book_list = get_all_books(db_conn)
    
    books = ["-- 도서를 선택하세요 --"] + st.session_state.book_list
    
    tab1, tab2 = st.tabs(["고객 및 주문 조회", "신규 거래 입력"])
    
    # === 탭 1: 고객 및 주문 조회 ===
    with tab1:
        name_input = st.text_input("조회할 고객 이름 입력:", key="cust_name_search") 
        
        if name_input:
            df_orders, cust_id = search_user_orders(name_input, db_conn)
            
            if not df_orders.empty:
                st.success(f"'{name_input}' 고객의 주문 내역입니다. (총 {len(df_orders)}건)", icon="🔎")
                st.dataframe(df_orders, use_container_width=True)
            elif cust_id is not None:
                 st.info(f"'{name_input}' 고객은 등록되어 있지만, 주문 내역이 없습니다. (고객 ID: {cust_id})")
            else:
                st.warning(f"'{name_input}' 고객을 찾을 수 없습니다. 이름 철자를 확인해주세요.")


    # === 탭 2: 신규 거래 입력 ===
    with tab2:
        # 1. 고객명 입력 및 ID 찾기
        input_name = st.text_input("거래할 고객 이름 입력:", key="cust_name_trade")
        
        current_custid = None
        if input_name:
            _, current_custid = search_user_orders(input_name, db_conn)
            
            if current_custid:
                st.info(f"고객 ID: {current_custid} (거래 준비 완료)")
            else:
                st.error("거래를 진행할 고객이 데이터베이스에 존재하지 않습니다.")
                current_custid = None

        if current_custid:
            # 2. 도서 선택
            select_book = st.selectbox("구매할 도서 선택:", books, key="book_select")
            
            # 3. 금액 및 거래 입력
            if select_book != "-- 도서를 선택하세요 --":
                book_id = int(select_book.split(",")[0])
                
                try:
                    price = st.number_input("판매 금액 입력:", min_value=100, step=100, key="price_input")
                except ValueError:
                    st.warning("금액을 숫자로 입력해주세요.")
                    st.stop()
                
                if st.button('거래 입력 완료', use_container_width=True, type="primary"):
                    try:
                        new_order_id = get_max_order_id(db_conn) + 1
                        order_date = time.strftime('%Y-%m-%d')
                        
                        # SQL 인젝션 방지를 위해 %s 사용
                        sql_insert = """
                        INSERT INTO Orders (orderid, custid, bookid, saleprice, orderdate) 
                        VALUES (%s, %s, %s, %s, %s);
                        """
                        with db_conn.cursor() as cursor:
                            cursor.execute(sql_insert, (new_order_id, current_custid, book_id, price, order_date))
                        
                        db_conn.commit()
                        st.success(f'✅ 거래가 성공적으로 입력되었습니다! (주문 ID: {new_order_id})')
                        
                    except Exception as commit_e:
                        db_conn.rollback()
                        st.error("거래 입력 중 데이터베이스 오류 발생!")
                        st.exception(commit_e)
