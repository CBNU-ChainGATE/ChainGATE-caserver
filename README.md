# CA-server
CA server

# Setting

### 1. 필요 프로그램 설치 및 설정

```
### python 및 관련 모듈 설치
$ sudo yum update -y
$ sudo yum install -y python3 python3-pip openssl
$ pip3 install Flask pyOpenSSL

### 방화벽 설정
$ sudo systemctl start firewalld
$ sudo systemctl enable firewalld
$ sudo firewall-cmd --zone=public --add-port=1441/tcp --permanent

### openssl 설치 및 개인키, 인증서, CRL 발급
$ sudo yum install openssh-server
$ mkdir certs
$ openssl genpkey -algorithm RSA -out certs/ca_key.pem -aes256                             # CA 개인키 생성
$ openssl req -new -x509 -days 365 -key certs/ca_key.pem -out certs/ca_cert.pem            # CA 인증서 생성
$ openssl ca -gencrl -keyfile certs/ca_key.pem -cert certs/ca_cert.pem -out certs/crl.pem  # CA CRL 생성
```

### 2. Git Repository 및 필요 파일 생성

```
$ git clone https://github.com/DDongu/ChainGATE-caserver.git
$ cd ChainGATE-caserver/
$ vi config.py      # 아래 config.py 파일을 서버 환경에 맞게 작성
```

_config.py_

```
CA_CERT_PATH = 'certs/ca_cert.pem'
CA_KEY_PATH = 'certs/ca_key.pem'
CA_KEY_PASSWORD = '인증서 비밀번호'
CRL_PATH = 'certs/crl.pem'
CERTS_DIR = 'certs/'
PORT = 1441          # 위에서 방화벽 설정한 포트
```

# How to start the CA server

```
$ cd ChainGATE-caserver/
$ python3 app.py
```

# CA Server API GUIDE
### 1. /api/v1/cert/request [POST]
  { 'csr': csr }

|  Key   |         Value         |   Type    |
| :----: | :-------------------: | :-------: |
| "csr" |  인증서 서명 요청 파일  | .pem 파일 |

**response**

서명된 파일(node_cert.pem)


### 2. /api/v1/cert/verify [POST]
  { 'cert': cert }

|  Key   |         Value         |   Type    |
| :----: | :-------------------: | :-------: |
| "cert" |  CA에서 서명된 인증서  | .pem 파일 |

**response**

200: 인증 성공

400: 등록되지 않은 혹은 파기된 인증서인 경우

500: 서버 에러


### 3. /api/blockchain/new [POST]

    {
        "date": "2024-04-12",
        "time": "10:30:00",
        "name": "홍길동",
        "position": "팀원",
        "department": "개발부"
    }

|     Key      |    Value    |        Type         |
| :----------: | :---------: | :-----------------: |
|    "date"    |  출입날짜   | String [YYYY-MM-DD] |
|    "time"    |  출입시간   |  String [HH:MM:SS]  |
|    "name"    | 출입자 이름 |       String        |
|  "position"  | 출입자 직급 |       String        |
| "department" | 출입자 소속 |       String        |


### 4. /api/blockchain/search [POST]

    {
        "date": "2024-04-12",
        "name": "",
        "department": "개발부"
    }

|     Key      |    Value    |           Type            |
| :----------: | :---------: | :-----------------------: |
|    "date"    |  출입날짜   | String [YYYY-MM-DD] OR "" |
|    "name"    | 출입자 이름 |       String OR ""        |
| "department" | 출입자 소속 |       String OR ""        |

**❗ 데이터가 없을 경우, _Value=""_ (최소 1개 이상의 데이터는 있어야 됨).**

**response**

200: 인증 성공

409: 블록체인 노드 간의 블록이 일치하지 않을 경우
