import streamlit as st 
import pymysql
import pandas as pd
import time

try:
    dbConn = pymysql.connect(
        user='root', 
        passwd='1234', 
        host='192.168.0.11',
        db='madang', 
        charset='utf8'
    )
    cursor = dbConn.cursor(pymysql.cursors.DictCursor)
    st.success("데이터베이스 연결 성공!")

except Exception as e:
    st.error(f"데이터베이스 연결 실패! 오류: {e}")
    st.warning("1. 'host' 주소가 정확한 '공인 IP'인지 확인하세요.")
    st.warning("2. MySQL 서버의 방화벽(3306 포트)과 공유기 포트 포워딩 설정을 확인하세요.")
    st.stop()
    
# --- DB 쿼리 함수 ---
def query(sql):
       cursor.execute(sql)
       return cursor.fetchall()

books = [None]
result = query("select concat(bookid, ',', bookname) from Book")
for res in result:
       books.append(list(res.values())[0])

tab1, tab2 = st.tabs(["고객조회", "거래 입력"])
name = ""
custid = 999
result =pd.DataFrame()
name = tab1.text_input("고객명")
select_book = ""

if len(name) > 0:
       # 고객 정보 및 거래 내역 조회
       sql = "select c.custid, c.name, b.bookname, o.orderdate, o.saleprice from Customer c, Book b, Orders o \
              where c.custid = o.custid and o.bookid = b.bookid and name = '" + name + "';"
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
              orderid = (max_orderid_result[0]['max(orderid)'] if max_orderid_result[0]['max(orderid)'] is not None else 0) + 1
              
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

