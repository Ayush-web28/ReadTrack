import { useCallback, useEffect, useState } from 'react'

/*
  useAsync(fn, deps): run an async function when the component appears (and
  whenever `deps` change), and track its three states.

      const { data, error, loading, reload } = useAsync(() => gql(QUERY), [])

  `reload()` runs it again, e.g. after the user changes something.
*/
export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true })

  const run = useCallback(() => {
    let cancelled = false   // ignore the result if the component left or deps changed
    setState((s) => ({ ...s, loading: true, error: null }))
    fn()
      .then((data) => !cancelled && setState({ data, error: null, loading: false }))
      .catch((error) => !cancelled && setState({ data: null, error, loading: false }))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => run(), [run])

  return { ...state, reload: run }
}
