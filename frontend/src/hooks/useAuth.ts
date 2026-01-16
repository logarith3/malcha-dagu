/**
 * SSO 인증 상태 확인 Hook.
 * Dagu 백엔드 API를 통해 HttpOnly 쿠키 인증 상태 확인.
 */

import { useState, useEffect } from 'react';

interface AuthState {
    isLoggedIn: boolean;
    isLoading: boolean;
    userId: number | null;
    username: string | null;
}

/**
 * 로그인 상태 확인 Hook
 * HttpOnly 쿠키는 JS에서 읽을 수 없으므로 백엔드 API로 확인
 */
export function useAuth(): AuthState {
    const [state, setState] = useState<AuthState>({
        isLoggedIn: false,
        isLoading: true,
        userId: null,
        username: null,
    });

    useEffect(() => {
        const checkAuth = async () => {
            try {
                const response = await fetch('/api/auth/check/', {
                    credentials: 'include', // 쿠키 포함 (vite 프록시 경유)
                });

                if (response.ok) {
                    const data = await response.json();
                    setState({
                        isLoggedIn: data.is_authenticated,
                        isLoading: false,
                        userId: data.user_id || null,
                        username: data.username || null,
                    });
                } else {
                    setState({
                        isLoggedIn: false,
                        isLoading: false,
                        userId: null,
                        username: null,
                    });
                }
            } catch (error) {
                console.error('Auth check failed:', error);
                setState({
                    isLoggedIn: false,
                    isLoading: false,
                    userId: null,
                    username: null,
                });
            }
        };

        checkAuth();
    }, []);

    return state;
}

export default useAuth;
