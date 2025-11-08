import streamlit as st 
import pymysql
import pandas as pd
import time

# --- DB 접속 정보 (최종 수정 부분) ---
# 🚨 주의: 'YOUR_PUBLIC_IP_ADDRESS_HERE'를 Windows PC의 실제 공인 IP 주소로 교체하세요!
# 🚨 주의: 'madang_user_비밀번호'를 실제 비밀번호로 교체하세요!

try:
    dbConn = pymysql.connect(
        user='madang_user', 
        passwd='madang_user_비밀번호', 
        host='YOUR_PUBLIC_IP_ADDRESS_HERE', # <--- 여기에 Windows PC의 공인 IP 주소 입력
        db='madang', 
        charset='utf8'
    )
    cursor = dbConn.cursor(pymysql.cursors.DictCursor)
    st.success("데이터베이스 연결 성공! Streamlit Cloud에서 DB에 접속했습니다.")

except Exception as e:
    st.error(f"데이터베이스 연결 실패! 오류: {e}")
    st.warning("1. 공인 IP 주소가 정확한지 확인하세요.")
    st.warning("2. Windows 방화벽(3306 포트)이 열려 있는지 확인하세요.")
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
       cursor.execute(sql)
       result = cursor.fetchall()
       
       if not result:
              tab1.warning(f"고객명 '{name}'의 거래 내역을 찾을 수 없습니다.")
              # 거래가 없는 고객의 custid만 찾기
              sql_cust = f"select custid from Customer where name = '{name}'"
              cursor.execute(sql_cust)
              cust_result = cursor.fetchone()
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
                                   # 디버깅을 위해 SQL 오류 메시지를 보여줄 수 있습니다.
                                   # tab2.code(commit_e)
              elif price:
                    tab2.warning("금액은 0보다 큰 숫자여야 합니다.")
