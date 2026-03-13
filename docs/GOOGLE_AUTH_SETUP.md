# Supabase Google OAuth 설정 가이드

이 문서는 Supabase 프로젝트에 Google 로그인을 연동하는 방법을 단계별로 안내합니다.

---

## 사전 준비

- Google 계정 (Gmail)
- Supabase 프로젝트 (이미 생성됨: `ytgbjsdffvfcguehtquv.supabase.co`)

---

## 1단계: Google Cloud Console에서 프로젝트 설정

1. [Google Cloud Console](https://console.cloud.google.com) 접속
2. 좌측 상단 프로젝트 선택 드롭다운 클릭
3. **새 프로젝트** 클릭 (또는 기존 프로젝트 선택)
   - 프로젝트 이름: `Invest Cockpit` (원하는 이름)
   - **만들기** 클릭

---

## 2단계: OAuth 동의 화면 구성

1. 좌측 메뉴에서 **APIs & Services** > **OAuth consent screen** 클릭
2. User Type: **External** 선택 > **만들기**
3. 필수 항목 입력:
   - **앱 이름**: `Invest Cockpit`
   - **사용자 지원 이메일**: 본인 Gmail 선택
   - **개발자 연락처 이메일**: 본인 Gmail 입력
4. **저장 후 계속** 클릭
5. Scopes 페이지: 변경 없이 **저장 후 계속**
6. Test users 페이지: 본인 Gmail 추가 > **저장 후 계속**
7. 요약 확인 후 **대시보드로 돌아가기**

> **참고**: 테스트 모드에서는 등록된 테스트 사용자만 로그인 가능합니다.
> 모든 사용자가 로그인하게 하려면 나중에 "앱 게시"를 진행하세요.

---

## 3단계: OAuth 2.0 Client ID 생성

1. 좌측 메뉴에서 **APIs & Services** > **Credentials** 클릭
2. 상단 **+ CREATE CREDENTIALS** > **OAuth client ID** 선택
3. 아래 항목 입력:
   - **Application type**: `Web application`
   - **Name**: `Supabase Auth` (원하는 이름)
   - **Authorized JavaScript origins**: (비워둠 — 필요시 추가)
   - **Authorized redirect URIs**: 아래 URI 추가

```
https://ytgbjsdffvfcguehtquv.supabase.co/auth/v1/callback
```

4. **만들기** 클릭
5. 팝업에 표시되는 **Client ID**와 **Client Secret**을 복사하여 안전한 곳에 저장

> 예시 형태:
> - Client ID: `123456789-abcdef.apps.googleusercontent.com`
> - Client Secret: `GOCSPX-xxxxxxxxxxxxxxxxx`

---

## 4단계: Supabase에서 Google Provider 활성화

1. [Supabase Dashboard](https://supabase.com/dashboard) 접속 > 프로젝트 선택
2. 좌측 메뉴에서 **Authentication** > **Providers** 클릭
3. 목록에서 **Google** 찾기 > 토글 켜기 (Enable)
4. 아래 항목 입력:
   - **Client ID**: 3단계에서 복사한 Client ID 붙여넣기
   - **Client Secret**: 3단계에서 복사한 Client Secret 붙여넣기
5. **Save** 클릭

---

## 5단계: 프론트엔드 연동 코드

Supabase JS 클라이언트를 사용하여 Google 로그인을 호출합니다.

### 로그인 버튼 (JavaScript)

```javascript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'https://ytgbjsdffvfcguehtquv.supabase.co',
  'YOUR_SUPABASE_ANON_KEY'
)

async function signInWithGoogle() {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: window.location.origin  // 로그인 후 돌아올 URL
    }
  })
  if (error) console.error('로그인 실패:', error.message)
}
```

### 로그아웃

```javascript
async function signOut() {
  const { error } = await supabase.auth.signOut()
  if (error) console.error('로그아웃 실패:', error.message)
}
```

### 현재 세션 확인

```javascript
const { data: { session } } = await supabase.auth.getSession()
if (session) {
  console.log('로그인됨:', session.user.email)
} else {
  console.log('로그인 안 됨')
}
```

---

## 6단계: 테스트

1. 앱에서 Google 로그인 버튼 클릭
2. Google 계정 선택 화면이 나타남
3. 계정 선택 후 동의 > Supabase redirect URI로 돌아옴
4. Supabase Dashboard > **Authentication** > **Users** 에서 새 사용자 확인

### 문제 해결 체크리스트

| 증상 | 확인 사항 |
|------|-----------|
| `redirect_uri_mismatch` 오류 | Google Cloud Console의 Authorized redirect URI가 정확한지 확인. 끝에 `/` 없이 입력: `https://ytgbjsdffvfcguehtquv.supabase.co/auth/v1/callback` |
| `access_denied` 오류 | OAuth 동의 화면이 테스트 모드인 경우, 본인 이메일이 테스트 사용자에 등록되어 있는지 확인 |
| 로그인 후 빈 화면 | `redirectTo` 파라미터가 올바른 앱 URL인지 확인 |
| `invalid_client` 오류 | Client ID / Secret이 Supabase에 정확히 입력되었는지 확인 |

---

## 보안 참고사항

- **Client Secret**은 절대 프론트엔드 코드에 노출하지 마세요 (Supabase가 서버사이드에서 관리)
- `api.env` 파일에 Client ID/Secret을 저장할 때는 `.gitignore`에 포함되어 있는지 확인
- 프로덕션 배포 시 OAuth 동의 화면을 "테스트"에서 "프로덕션"으로 전환 필요
