---
name: project_tech_stack
description: 2026-03-12 승인된 기술 스택 및 아키텍처 결정사항
type: project
---

4개 페이지 웹 서비스(인사이트 블로그, 실시간 주식가격, 포트폴리오 관리, AI 챗봇)의 기술 스택이 확정됨.

**Frontend**: Vanilla JS + Alpine.js + Tailwind CSS 4 + Chart.js (빌드 단계 없음, CDN 기반)
**BaaS**: Supabase (Auth, PostgreSQL DB, Edge Functions, Storage) — 무료 티어
**Hosting**: GitHub Pages (docs/ 폴더, 기존 유지)
**AI**: Claude API → Supabase Edge Function 프록시로 호출 (API 키 보호)

**Why:** 사용자가 비개발자이며 10명 이하 소규모 서비스. React/Vue 같은 프레임워크는 빌드 도구와 Node.js 관리 부담이 과도함.
**How to apply:** 모든 FE 코드는 빌드 단계 없이 CDN + HTML 파일로 작성. BaaS 로직은 Supabase로 통일. 새로운 프레임워크/도구 도입 시 반드시 사용자 승인 필요.
