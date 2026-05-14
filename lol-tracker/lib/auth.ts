export function isAdmin(request: Request): boolean {
  const auth = request.headers.get('authorization')
  if (!auth) return false
  const token = auth.replace('Bearer ', '')
  return token === process.env.ADMIN_PASSWORD
}
