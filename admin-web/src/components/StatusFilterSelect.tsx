import { Select } from 'antd'
import type { StatusFilter } from '../api/types'

type StatusFilterSelectProps = {
  value: StatusFilter
  onChange: (value: StatusFilter) => void
}

export function StatusFilterSelect({
  value,
  onChange,
}: StatusFilterSelectProps) {
  return (
    <Select<StatusFilter>
      value={value}
      style={{ width: 120 }}
      onChange={onChange}
      options={[
        { value: 'all', label: '全部' },
        { value: 'active', label: '启用' },
        { value: 'inactive', label: '停用' },
      ]}
    />
  )
}
