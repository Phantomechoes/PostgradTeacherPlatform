import { Button, Popconfirm } from 'antd'

type EntityStatusActionProps = {
  active: boolean
  loading?: boolean
  confirmTitle: string
  onChange: (active: boolean) => void
}

export function EntityStatusAction({
  active,
  loading = false,
  confirmTitle,
  onChange,
}: EntityStatusActionProps) {
  if (!active) {
    return (
      <Button
        type="link"
        loading={loading}
        disabled={loading}
        onClick={() => onChange(true)}
      >
        恢复
      </Button>
    )
  }
  return (
    <Popconfirm
      title={confirmTitle}
      description="停用不会删除数据。"
      okText="停用"
      cancelText="取消"
      onConfirm={() => onChange(false)}
    >
      <Button type="link" danger loading={loading} disabled={loading}>
        停用
      </Button>
    </Popconfirm>
  )
}
