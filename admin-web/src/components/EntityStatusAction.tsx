import { Button, Popconfirm } from 'antd'

type EntityStatusActionProps = {
  active: boolean
  loading?: boolean
  disabled?: boolean
  confirmTitle: string
  description?: string
  onChange: (active: boolean) => void
}

export function EntityStatusAction({
  active,
  loading = false,
  disabled = false,
  confirmTitle,
  description = '停用不会删除数据。',
  onChange,
}: EntityStatusActionProps) {
  const blocked = loading || disabled
  if (!active) {
    return (
      <Button
        type="link"
        loading={loading}
        disabled={blocked}
        onClick={() => onChange(true)}
      >
        恢复
      </Button>
    )
  }
  return (
    <Popconfirm
      title={confirmTitle}
      description={description}
      okText="停用"
      cancelText="取消"
      disabled={blocked}
      onConfirm={() => onChange(false)}
    >
      <Button type="link" danger loading={loading} disabled={blocked}>
        停用
      </Button>
    </Popconfirm>
  )
}
