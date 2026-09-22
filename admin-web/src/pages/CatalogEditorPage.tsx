import {
  Alert,
  App,
  Button,
  Card,
  Input,
  InputNumber,
  Popconfirm,
  Result,
  Select,
  Space,
  Typography,
} from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  getCatalog,
  replaceCatalogAggregate,
  setCatalogStatus,
} from '../api/catalog'
import { ApiError, isAbortError } from '../api/client'
import { errorText } from '../api/formErrors'
import {
  listAllSchools,
  listColleges,
  listMajors,
  listNationalSubjects,
  listSchoolSubjects,
} from '../api/masterData'
import type {
  CatalogAdminDetail,
  CatalogAggregatePut,
  CollegeAdmin,
  ExamSubjectAdmin,
  MajorAdmin,
  SchoolAdmin,
  StudyMode,
} from '../api/types'
import { StatusTag } from '../components/StatusTag'
import {
  buildPut,
  draftFromDetail,
  putFromDetail,
  referencedSubjects,
  samePut,
  type CatalogDraft,
  type UnitDraft,
} from '../features/catalog/editorState'
import {
  entityLabel,
  newRowKey,
  STUDY_MODE_LABEL,
} from '../features/catalog/labels'
import { SubjectPicker } from '../features/catalog/SubjectPicker'

function parseCatalogId(value: string | undefined): number | null {
  if (!value) {
    return null
  }
  const id = Number(value)
  return Number.isInteger(id) && id > 0 ? id : null
}

const EMPTY_DIRECTIONS_HINT = '当前研究方向将全部清空。确认保存整份目录？'
const EMPTY_UNITS_HINT = '当前考试科目将全部清空。确认保存整份目录？'

export function CatalogEditorPage() {
  const { catalogId } = useParams()
  const id = parseCatalogId(catalogId)
  const navigate = useNavigate()
  const { message, modal } = App.useApp()
  const [reloadKey, setReloadKey] = useState(0)
  const requestKey = `${id}|${reloadKey}`
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState<CatalogAdminDetail | null>(null)
  const [draft, setDraft] = useState<CatalogDraft | null>(null)
  const [seenKey, setSeenKey] = useState(requestKey)
  if (seenKey !== requestKey) {
    setSeenKey(requestKey)
    setLoading(true)
    setNotFound(false)
    setError(null)
    setSaved(null)
    setDraft(null)
  }
  const [schools, setSchools] = useState<SchoolAdmin[]>([])
  const schoolId = draft?.schoolId
  const childKey = schoolId ?? 0
  const [childLists, setChildLists] = useState<{
    key: number
    colleges: CollegeAdmin[]
    majors: MajorAdmin[]
    subjects: ExamSubjectAdmin[]
  }>({ key: childKey, colleges: [], majors: [], subjects: [] })
  if (childLists.key !== childKey) {
    setChildLists({
      key: childKey,
      colleges: [],
      majors: [],
      subjects: [],
    })
  }
  const colleges = childLists.colleges
  const majors = childLists.majors
  const subjects = childLists.subjects
  const [saving, setSaving] = useState(false)
  const [statusLoading, setStatusLoading] = useState(false)

  useEffect(() => {
    if (id === null) {
      return
    }
    const controller = new AbortController()
    getCatalog(id, { signal: controller.signal })
      .then((detail) => {
        if (controller.signal.aborted) {
          return
        }
        setSaved(detail)
        setDraft(draftFromDetail(detail))
      })
      .catch((loadError: unknown) => {
        if (isAbortError(loadError) || controller.signal.aborted) {
          return
        }
        if (
          loadError instanceof ApiError &&
          (loadError.status === 404 || loadError.code === 'not_found')
        ) {
          setNotFound(true)
          return
        }
        setError(loadError instanceof ApiError ? loadError.message : '请求失败')
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      })
    return () => controller.abort()
  }, [id, reloadKey])

  useEffect(() => {
    const controller = new AbortController()
    listAllSchools('all', { signal: controller.signal })
      .then(setSchools)
      .catch(() => {
        if (!controller.signal.aborted) {
          setSchools([])
        }
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (!schoolId) {
      return
    }
    const controller = new AbortController()
    const key = schoolId
    Promise.all([
      listColleges(schoolId, 'all', { signal: controller.signal }),
      listMajors(schoolId, 'all', { signal: controller.signal }),
      listNationalSubjects('all', { signal: controller.signal }),
      listSchoolSubjects(schoolId, 'all', { signal: controller.signal }),
    ])
      .then(([nextColleges, nextMajors, national, schoolSubjects]) => {
        setChildLists((current) =>
          current.key === key
            ? {
                key,
                colleges: nextColleges,
                majors: nextMajors,
                subjects: [...national, ...schoolSubjects],
              }
            : current,
        )
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setChildLists((current) =>
            current.key === key
              ? { key, colleges: [], majors: [], subjects: [] }
              : current,
          )
        }
      })
    return () => controller.abort()
  }, [schoolId])

  const extras = saved ? referencedSubjects(saved) : []
  const built = draft ? buildPut(draft) : null
  const savedPut = saved ? putFromDetail(saved) : null
  const dirty = Boolean(
    draft &&
    savedPut &&
    (built === null || !built.ok || !samePut(built.body, savedPut)),
  )

  const unusedUnits = useMemo(() => {
    const used = new Set(draft?.units.map((unit) => unit.exam_unit) ?? [])
    return [1, 2, 3, 4].filter((unit) => !used.has(unit))
  }, [draft])

  function patchDraft(patch: Partial<CatalogDraft>) {
    setDraft((current) => (current ? { ...current, ...patch } : current))
  }

  async function persist(body: CatalogAggregatePut) {
    if (!saved || saving) {
      return
    }
    setSaving(true)
    try {
      const updated = await replaceCatalogAggregate(saved.id, body)
      setSaved(updated)
      setDraft(draftFromDetail(updated))
      message.success('招生目录已保存')
    } catch (saveError: unknown) {
      message.error(errorText(saveError))
    } finally {
      setSaving(false)
    }
  }

  function confirmEmptyThenSave(body: CatalogAggregatePut) {
    if (!savedPut) {
      return
    }
    const clearDirections =
      savedPut.directions.length > 0 && body.directions.length === 0
    const clearUnits =
      savedPut.exam_units.length > 0 && body.exam_units.length === 0
    if (!clearDirections && !clearUnits) {
      void persist(body)
      return
    }
    const hints = [
      clearDirections ? EMPTY_DIRECTIONS_HINT : null,
      clearUnits ? EMPTY_UNITS_HINT : null,
    ].filter((item): item is string => item !== null)
    modal.confirm({
      title: '确认清空集合？',
      content: hints.join(' '),
      okText: '确认保存',
      cancelText: '取消',
      onOk: () => persist(body),
    })
  }

  function save() {
    if (!draft) {
      return
    }
    const result = buildPut(draft)
    if (!result.ok) {
      message.error(result.error)
      return
    }
    confirmEmptyThenSave(result.body)
  }

  async function changeStatus(next: boolean) {
    if (!saved || statusLoading) {
      return
    }
    if (dirty) {
      modal.confirm({
        title: '有未保存的修改',
        content: '请先保存整份目录，或放弃修改后再公开 / 取消公开。',
        okText: '放弃修改',
        cancelText: '取消',
        onOk: () => {
          setDraft(draftFromDetail(saved))
        },
      })
      return
    }
    setStatusLoading(true)
    try {
      const updated = await setCatalogStatus(saved.id, next)
      setSaved(updated)
      setDraft(draftFromDetail(updated))
      message.success(next ? '目录已公开' : '目录已取消公开')
    } catch (statusError: unknown) {
      message.error(errorText(statusError))
    } finally {
      setStatusLoading(false)
    }
  }

  if (id === null || notFound) {
    return <Result status="404" title="未找到招生目录" />
  }
  if (error) {
    return (
      <Alert
        type="error"
        showIcon
        message={error}
        action={
          <Button
            size="small"
            onClick={() => setReloadKey((value) => value + 1)}
          >
            重试
          </Button>
        }
      />
    )
  }
  if (loading || !saved || !draft) {
    return <Typography.Paragraph>正在加载招生目录…</Typography.Paragraph>
  }

  return (
    <>
      <Space
        wrap
        style={{ width: '100%', justifyContent: 'space-between' }}
        align="start"
      >
        <div>
          <Typography.Title level={3} style={{ marginBottom: 8 }}>
            招生目录 {saved.admission_year} {STUDY_MODE_LABEL[saved.study_mode]}
          </Typography.Title>
          <Space>
            <Typography.Text>
              {saved.school.school_code} {saved.school.name}
            </Typography.Text>
            <StatusTag mode="catalog" active={saved.is_active} />
          </Space>
        </div>
        <Space>
          <Button
            onClick={() => navigate(`/catalogs?school_id=${draft.schoolId}`)}
          >
            返回列表
          </Button>
          <Button type="primary" loading={saving} onClick={save}>
            保存整份目录
          </Button>
          {saved.is_active ? (
            <Popconfirm
              title="确认取消公开？"
              description="取消公开不会删除方向和考试科目。"
              okText="取消公开"
              cancelText="返回"
              onConfirm={() => void changeStatus(false)}
            >
              <Button loading={statusLoading} disabled={statusLoading}>
                取消公开
              </Button>
            </Popconfirm>
          ) : (
            <Button
              loading={statusLoading}
              disabled={statusLoading}
              onClick={() => void changeStatus(true)}
            >
              公开
            </Button>
          )}
        </Space>
      </Space>

      <Card title="基本信息" style={{ marginTop: 16 }}>
        <Space wrap>
          <label>
            院校
            <Select
              showSearch
              optionFilterProp="label"
              style={{ width: 280, marginLeft: 8 }}
              value={draft.schoolId}
              onChange={(value) =>
                patchDraft({
                  schoolId: value,
                  collegeId: 0,
                  majorId: 0,
                })
              }
              options={schools.map((school) => ({
                value: school.id,
                label: entityLabel(
                  school.school_code,
                  school.name,
                  school.is_active,
                ),
              }))}
            />
          </label>
          <label>
            学院
            <Select
              showSearch
              optionFilterProp="label"
              style={{ width: 240, marginLeft: 8 }}
              value={draft.collegeId || undefined}
              onChange={(value) => patchDraft({ collegeId: value })}
              options={colleges.map((college) => ({
                value: college.id,
                label: entityLabel(
                  college.college_code,
                  college.name,
                  college.is_active,
                ),
              }))}
            />
          </label>
          <label>
            专业
            <Select
              showSearch
              optionFilterProp="label"
              style={{ width: 240, marginLeft: 8 }}
              value={draft.majorId || undefined}
              onChange={(value) => patchDraft({ majorId: value })}
              options={majors.map((major) => ({
                value: major.id,
                label: entityLabel(
                  major.major_code,
                  major.name,
                  major.is_active,
                ),
              }))}
            />
          </label>
          <label>
            年份
            <InputNumber
              min={2000}
              style={{ width: 120, marginLeft: 8 }}
              value={draft.admissionYear}
              onChange={(value) => {
                if (typeof value === 'number') {
                  patchDraft({ admissionYear: value })
                }
              }}
            />
          </label>
          <label>
            学习方式
            <Select
              style={{ width: 140, marginLeft: 8 }}
              value={draft.studyMode}
              onChange={(value: StudyMode) => patchDraft({ studyMode: value })}
              options={(Object.keys(STUDY_MODE_LABEL) as StudyMode[]).map(
                (value) => ({
                  value,
                  label: STUDY_MODE_LABEL[value],
                }),
              )}
            />
          </label>
        </Space>
      </Card>

      <Card
        title="研究方向"
        style={{ marginTop: 16 }}
        extra={
          <Button
            onClick={() =>
              patchDraft({
                directions: [
                  ...draft.directions,
                  {
                    key: newRowKey(),
                    direction_code: '',
                    direction_name: '',
                  },
                ],
              })
            }
          >
            添加方向
          </Button>
        }
      >
        {draft.directions.length === 0 ? (
          <Typography.Text type="secondary">
            没有研究方向。空集合可以保存。
          </Typography.Text>
        ) : (
          draft.directions.map((row, index) => (
            <Space key={row.key} style={{ display: 'flex', marginBottom: 8 }}>
              <Input
                placeholder="方向代码"
                value={row.direction_code}
                maxLength={32}
                style={{ width: 160 }}
                onChange={(event) => {
                  const directions = draft.directions.map((item, itemIndex) =>
                    itemIndex === index
                      ? { ...item, direction_code: event.target.value }
                      : item,
                  )
                  patchDraft({ directions })
                }}
              />
              <Input
                placeholder="方向名称"
                value={row.direction_name}
                maxLength={255}
                style={{ width: 280 }}
                onChange={(event) => {
                  const directions = draft.directions.map((item, itemIndex) =>
                    itemIndex === index
                      ? { ...item, direction_name: event.target.value }
                      : item,
                  )
                  patchDraft({ directions })
                }}
              />
              <Button
                onClick={() =>
                  patchDraft({
                    directions: draft.directions.filter(
                      (_, itemIndex) => itemIndex !== index,
                    ),
                  })
                }
              >
                删除
              </Button>
            </Space>
          ))
        )}
      </Card>

      <Card
        title="考试单元"
        style={{ marginTop: 16 }}
        extra={
          unusedUnits.length === 0 ? null : (
            <Select
              placeholder="添加考试单元"
              style={{ width: 160 }}
              value={undefined}
              onChange={(unit: number) =>
                patchDraft({
                  units: [
                    ...draft.units,
                    {
                      key: newRowKey(),
                      exam_unit: unit,
                      options: [
                        {
                          key: newRowKey(),
                          option_order: 1,
                          exam_subject_id: null,
                        },
                      ],
                    },
                  ].sort((left, right) => left.exam_unit - right.exam_unit),
                })
              }
              options={unusedUnits.map((unit) => ({
                value: unit,
                label: `单元 ${unit}`,
              }))}
            />
          )
        }
      >
        {draft.units.length === 0 ? (
          <Typography.Text type="secondary">
            没有考试单元。空集合可以保存，也可以公开。
          </Typography.Text>
        ) : (
          draft.units.map((unit) => (
            <ExamUnitEditor
              key={unit.key}
              unit={unit}
              schoolId={draft.schoolId}
              subjects={subjects}
              extras={extras}
              onChange={(next) =>
                patchDraft({
                  units: draft.units.map((item) =>
                    item.key === unit.key ? next : item,
                  ),
                })
              }
              onRemove={() =>
                patchDraft({
                  units: draft.units.filter((item) => item.key !== unit.key),
                })
              }
            />
          ))
        )}
      </Card>
    </>
  )
}

function ExamUnitEditor({
  unit,
  schoolId,
  subjects,
  extras,
  onChange,
  onRemove,
}: {
  unit: UnitDraft
  schoolId: number
  subjects: ExamSubjectAdmin[]
  extras: ExamSubjectAdmin[]
  onChange: (unit: UnitDraft) => void
  onRemove: () => void
}) {
  return (
    <Card
      size="small"
      type="inner"
      title={`考试单元 ${unit.exam_unit}（同一单元多个科目为 OR）`}
      style={{ marginBottom: 12 }}
      extra={
        <Button size="small" onClick={onRemove}>
          删除单元
        </Button>
      }
    >
      {unit.options.map((option, index) => (
        <Space key={option.key} style={{ display: 'flex', marginBottom: 8 }}>
          <InputNumber
            min={1}
            value={option.option_order}
            onChange={(value) => {
              if (typeof value !== 'number') {
                return
              }
              onChange({
                ...unit,
                options: unit.options.map((item, itemIndex) =>
                  itemIndex === index ? { ...item, option_order: value } : item,
                ),
              })
            }}
          />
          <div style={{ width: 420 }}>
            <SubjectPicker
              value={option.exam_subject_id}
              schoolId={schoolId}
              subjects={subjects}
              extras={extras}
              onChange={(exam_subject_id) =>
                onChange({
                  ...unit,
                  options: unit.options.map((item, itemIndex) =>
                    itemIndex === index ? { ...item, exam_subject_id } : item,
                  ),
                })
              }
            />
          </div>
          <Button
            onClick={() => {
              const options = unit.options.filter(
                (_, itemIndex) => itemIndex !== index,
              )
              if (options.length === 0) {
                onRemove()
                return
              }
              onChange({ ...unit, options })
            }}
          >
            删除选项
          </Button>
        </Space>
      ))}
      <Button
        onClick={() => {
          const maxOrder = unit.options.reduce(
            (max, option) => Math.max(max, option.option_order),
            0,
          )
          onChange({
            ...unit,
            options: [
              ...unit.options,
              {
                key: newRowKey(),
                option_order: maxOrder + 1,
                exam_subject_id: null,
              },
            ],
          })
        }}
      >
        添加科目选项
      </Button>
    </Card>
  )
}
