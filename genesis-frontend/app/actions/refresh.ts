'use server'

import { revalidatePath } from 'next/cache'

export async function forceRefreshAction(path: string) {
  // This invalidates the Next.js Server Cache for this URL
  revalidatePath(path)
}
