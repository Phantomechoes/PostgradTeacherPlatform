import type { TeacherAdminDetail, TeacherAdminSummary } from '../../api/types'

// Profile and status endpoints return Summary only. Keep the loaded collections.
export function mergeTeacherSummary(
  detail: TeacherAdminDetail,
  summary: TeacherAdminSummary,
): TeacherAdminDetail {
  return {
    ...detail,
    ...summary,
    admission_records: detail.admission_records,
    teach_subjects: detail.teach_subjects,
  }
}
