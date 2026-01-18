import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
// 함수 형태로 바꿔서 command(실행 명령어)를 확인합니다.
export default defineConfig(({ command }) => {
  const isBuild = command === 'build';

  return {
    plugins: [
      react(),
      tailwindcss(),
    ],
    // [핵심] 빌드할 때(배포용)는 '/static/', 로컬 개발일 때는 '/' 사용
    base: isBuild ? '/static/' : '/',

    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: 'http://localhost:8001',
          changeOrigin: true,
        },
      },
    },
  };
});