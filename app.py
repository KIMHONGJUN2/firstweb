from flask import Flask,render_template,redirect,request,jsonify,session,Response,send_file
import pymysql
import boto3
import os
from flask_restful import reqparse,abort,Api,Resource
from werkzeug.security import check_password_hash,generate_password_hash

app = Flask(__name__)
api = Api(app)  # 페이지 변경이 아니라 데이터만(파일만)

ssm = boto3.client('ssm')
parameter = ssm.get_parameter(Name = '/myweb/database1_password',WithDecryption = True)
db_password = parameter['Parameter']['Value']



@app.route('/')  # app = 플라스크 객체  , route 는 url을 결정해 줌
# 8080 서버 방 번호 // ip 내에 웹서버 동작 (플라스크가 띄움)

# def hello():
#     return 'hello Flask!<h1>'
#     # db 에서 불러와야될 것이 있다면 여기 작성
#     # html 파일을 넣어두는 약속 templates로 만들어야함
def index():
    # return '사용법 : url에  /board를 입력해주세요.'
    return redirect('/board')
def upload_file_to_bucket(file):
    BUCKET_NAME = 's3pbl'
    S3_KEY = 'images/' + file.filename
    s3 = boto3.client('s3')
    s3.put_object(  # boto3 가 가지고 있는 함수
        Bucket = BUCKET_NAME,
        Body = file,
        Key = S3_KEY,
        ContentType = file.content_type
    )


@app.route('/test')
def test():
    return 'test'

#새로운 페이지 추가
@app.route('/hello')
def hi():
    name = 'abc def ghi'
    return render_template('hello.html',name = name)


# 게시판
@app.route('/board')
def board_list():
    db = pymysql.connect(host='database-1.cqg3hgrpgtlh.ap-northeast-2.rds.amazonaws.com',
                         db='pblaws', port=3306,
                         passwd=db_password, user='admin')
    curs = db.cursor(pymysql.cursors.DictCursor)

    sql = 'SELECT * FROM board ORDER BY id DESC'
    curs.execute(sql)
    results = curs.fetchall()
    curs.close()
    db.close()
    print(results)
    return render_template('board_list.html', results = results)


@app.route('/board/writeform')
def board_writeform():
    return render_template('board_writeform.html')

@app.route('/board/write',methods = ['POST'])  # 기본은 GET 이지만 우리는  POST로 요청했기 때문에 POST로 설정해준다.
def write():
    if request.method == 'POST':
        name = request.form.get('name',False)   # input 에서 받은 name
        passwd = request.form.get('passwd', False)
        title = request.form.get('title', False)
        content = request.form.get('content', False)
        file = request.files['file']  # 5번 파일 업로드
        error = None

        # 아이디가 없으면
        if not name:
            error = 'name이 유효하지 않습니다.'
        elif not passwd:
            error = 'password가 유효하지 않습니다.'
        elif not title:
            error = 'title이 유효하지 않습니다.'
        elif not content:
            error = 'content 가 유효하지 않습니다.'


        # print(file)
        # print(file.content_length)   테스트용 없어도 됨
        if file:
            print('-----------------------------------------------')
            print(file)
            print('------------------------------------------------')
            image_url = upload_file_to_bucket(file)
            print(image_url)


            # 에러가 발생하지 않았다면 회원가입 실행

        if error is None:
            db = pymysql.connect(host='database-1.cqg3hgrpgtlh.ap-northeast-2.rds.amazonaws.com', port=3306,
                                 db='pblaws', passwd=db_password, user='admin')
            cursor = db.cursor()
            cursor.execute(
                'INSERT INTO board (name, passwd, title, content ) VALUES (%s, %s, %s, %s)',
                (name, generate_password_hash(passwd), title, content)
            )
            # 5번. 파일 업로드
            if file:
                cursor.execute('SELECT LAST_INSERT_ID()')
                result = cursor.fetchall()
                board_id = result[0][0]
                # s3_path는 s3_key를 의미한다.
                cursor.execute(
                    'INSERT INTO board_file (board_id, file_name, s3_bucket, s3_path, mime_type) VALUES (%s, %s, %s, %s, %s)',
                    (board_id, file.filename, 's3pbl', 'images/' + file.filename, file.content_type)
                )
            db.commit()
            cursor.close()
            db.close()

        return redirect('/board')

@app.route('/board/down', methods=['GET'])
def download():
    board_id = request.args['id']
    db = pymysql.connect(host='database-1.cqg3hgrpgtlh.ap-northeast-2.rds.amazonaws.com',port=3306,db='pblaws',passwd=db_password,user='admin')
    curs = db.cursor(pymysql.cursors.DictCursor)
    sql = 'SELECT * FROM board_file WHERE board_id = %s'
    curs.execute(sql, (board_id))
    result = curs.fetchone()
    curs.close()
    db.close()

    print("result : " , result)
    if result :
        BUCKET_NAME = 's3pbl'
        key = result['s3_path']
        file_name = result['file_name']
        file_content_type = result['mime_type']

        s3 = boto3.client('s3')
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.get_object
        file = s3.get_object(Bucket=BUCKET_NAME, Key=key)

        print(file)
        # S3의 파일정보의 Body(byte[])을 읽어들여 응답으로 출력한다.
        return Response(
            file['Body'].read(),
            mimetype=file_content_type #,
            #headers={"Content-Disposition": "attachment;filename=" + file_name}
        )
    else :
        print("-------------------------------------------------------------------")
        return send_file('nofile.png', mimetype='image/png')

@app.route('/board/view')
def board_view():
    board_id = request.args['id']
    print('board_id : ' + board_id)
    db = pymysql.connect(host='database-1.cqg3hgrpgtlh.ap-northeast-2.rds.amazonaws.com',port=3306,db='pblaws',passwd=db_password,user='admin')
    curs = db.cursor(pymysql.cursors.DictCursor)
    sql = 'SELECT * FROM board WHERE id = %s'
    curs.execute(sql, (board_id))
    result = curs.fetchone()
    curs.close()
    db.close()
    print(result)

    return render_template('board_view.html', result=result)


if __name__ == '__main__':
    app.run('0.0.0.0',port=8080)




