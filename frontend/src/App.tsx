/**
 * MALCHA-DAGU Main App
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import HomePage from './pages/HomePage';
import SearchResultPage from './pages/SearchResultPage';
import CategoryPage from './pages/CategoryPage';

// React Query 클라이언트 설정
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5분
      gcTime: 10 * 60 * 1000,   // 10분
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchResultPage />} />
          {/* Brand & Category Routes */}
          <Route path="/brand/:brand" element={<CategoryPage />} />
          <Route path="/category/:brand" element={<CategoryPage />} />
          <Route path="/category/:brand/:model" element={<CategoryPage />} />
          <Route path="/category/:brand/:model/:submodel" element={<CategoryPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
