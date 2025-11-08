import streamlit as st 
import pymysql
import pandas as pd
import time

# --- DB 접속 정보 (사설 IP 적용 - 로컬 환경 전용) ---
# 🚨 주의: 이 코드는 Streamlit Cloud에서는 작동하지 않으며, 로컬 환경 테스트 용도로만 사용 가능합니다.
try:
    dbConn = pymysql.connect(
        user='madang_user', 
        passwd='madang_user_1234', 
        host='192.168.0.11', # <--- 사설 IP 주소로 복구 (로컬 테스트용)
        db='madang', 
        charset='utf8'
    )
    cursor = dbConn.cursor(pymysql.cursors.DictCursor)
    st.success("데이터베이스 연결 성공! (로컬 네트워크 환경)", icon="✅")

except Exception as e:
    st.error(f"데이터베이스 연결 실패! 오류: {e}")
    st.warning("경고: Streamlit Cloud에서는 공인 IP 주소가 필요합니다.")
    st.stop()
# ------------------------------

def query(sql):
       cursor.execute(sql)
       return cursor.fetchall()

books = [None]
# DB 연결 문제로 쿼리 실행이 실패할 경우를 대비하여 try-except 블록 추가
try:
    result = query("select concat(bookid, ',', bookname) from Book")
    for res in result:
           books.append(list(res.values())[0])
except Exception as e:
    st.error(f"초기 데이터 로딩 실패: {e}")
    st.stop()


tab1, tab2 = st.tabs(["고객조회", "거래 입력"])
name = ""
custid = 999
result = pd.DataFrame()
name = tab1.text_input("고객명")
select_book = ""

if len(name) > 0:
       # 고객 정보 및 거래 내역 조회
       sql = f"select c.custid, c.name, b.bookname, o.orderdate, o.saleprice from Customer c, Book b, Orders o where c.custid = o.custid and o.bookid = b.bookid and name = '{name}';"
       
       try:
           cursor.execute(sql)
           result = cursor.fetchall()
       except Exception as e:
           st.error(f"고객 조회 중 오류 발생: {e}")
           st.stop()
           
       if not result:
              tab1.warning(f"고객명 '{name}'의 거래 내역을 찾을 수 없습니다.")
              # 거래가 없는 고객의 custid만 찾기
              sql_cust = f"select custid from Customer where name = '{name}'"
              
              try:
                  cursor.execute(sql_cust)
                  cust_result = cursor.fetchone()
              except Exception as e:
                   st.error(f"고객 ID 조회 중 오류 발생: {e}")
                   st.stop()
              
              if cust_result:
                  custid = cust_result['custid']
                  tab2.write(f"고객번호: {custid}")
                  tab2.write(f"고객명: {name}")
              else:
                  tab1.error(f"고객명 '{name}'은(는) 존재하지 않습니다.")
                  st.stop()
       else:
              result = pd.DataFrame(result)
              tab1.write(result)
              custid = result['custid'][0] 
              tab2.write(f"고객번호: {custid}")
              tab2.write(f"고객명: {name}")
       
       # 거래 입력 섹션
       select_book = tab2.selectbox("구매 서적:",books)
       
       if select_book and select_book is not None:
              bookid = select_book.split(",")[0]
              
              dt = time.localtime()
              dt = time.strftime('%Y-%m-%d', dt)
              
              # 새로운 orderid 생성
              max_orderid_result = query("select max(orderid) from orders;")
              # 결과가 None일 경우 0으로 처리하여 +1 (첫 주문 시)
              orderid = (max_orderid_result[0]['max(orderid)'] if max_orderid_result and max_orderid_result[0]['max(orderid)'] is not None else 0) + 1
              
              price = tab2.text_input("금액")
              
              if price.isdigit() and int(price) > 0:
                     sql = f"insert into orders (orderid, custid, bookid, saleprice, orderdate) values ({orderid}, {custid}, {bookid}, {price}, '{dt}');"
                     
                     if tab2.button('거래 입력'):
                            try:
                                   cursor.execute(sql)
                                   dbConn.commit()
                                   tab2.success(f'거래가 입력되었습니다. (Order ID: {orderid})')
                            except Exception as commit_e:
                                   dbConn.rollback()
                                   tab2.error(f"거래 입력 중 오류 발생: {commit_e}")
              elif price:
                    tab2.warning("금액은 0보다 큰 숫자여야 합니다.")
