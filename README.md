# CA-server
ca server

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
