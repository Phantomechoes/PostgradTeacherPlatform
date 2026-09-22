import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { CatalogEditorPage } from './pages/CatalogEditorPage'
import { CatalogsPage } from './pages/CatalogsPage'
import { NationalSubjectsPage } from './pages/NationalSubjectsPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { SchoolDetailPage } from './pages/SchoolDetailPage'
import { SchoolsPage } from './pages/SchoolsPage'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/schools" replace />} />
        <Route path="schools" element={<SchoolsPage />} />
        <Route path="schools/:schoolId" element={<SchoolDetailPage />} />
        <Route
          path="exam-subjects/national"
          element={<NationalSubjectsPage />}
        />
        <Route path="catalogs" element={<CatalogsPage />} />
        <Route path="catalogs/:catalogId" element={<CatalogEditorPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
