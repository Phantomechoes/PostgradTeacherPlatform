import { Tag } from 'antd'

type StatusTagProps =
  { mode: 'entity'; active: boolean } | { mode: 'catalog'; active: boolean }

export function StatusTag({ mode, active }: StatusTagProps) {
  if (mode === 'catalog') {
    return (
      <Tag color={active ? 'green' : 'default'}>
        {active ? '已公开' : '未公开'}
      </Tag>
    )
  }
  return (
    <Tag color={active ? 'green' : 'default'}>{active ? '启用' : '停用'}</Tag>
  )
}
