'use client'

import { Download } from 'lucide-react'

export default function RequestFlowDownloadButtons({
  svgId,
  svgHref,
  fileBase,
}: {
  svgId: string
  svgHref: string
  fileBase: string
}) {
  const downloadPng = async () => {
    const svg = document.getElementById(svgId)
    if (!(svg instanceof SVGSVGElement)) return

    const serializer = new XMLSerializer()
    const source = serializer.serializeToString(svg)
    const blob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const image = new Image()
    image.onload = () => {
      const scale = 2
      const canvas = document.createElement('canvas')
      canvas.width = image.width * scale
      canvas.height = image.height * scale
      const context = canvas.getContext('2d')
      if (!context) return
      context.fillStyle = '#f8fbff'
      context.fillRect(0, 0, canvas.width, canvas.height)
      context.scale(scale, scale)
      context.drawImage(image, 0, 0)
      URL.revokeObjectURL(url)
      const link = document.createElement('a')
      link.download = `${fileBase}.png`
      link.href = canvas.toDataURL('image/png')
      link.click()
    }
    image.src = url
  }

  return (
    <>
      <a
        href={svgHref}
        download={`${fileBase}.svg`}
        className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
      >
        SVG <Download className="h-3.5 w-3.5" />
      </a>
      <button
        type="button"
        onClick={downloadPng}
        className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
      >
        PNG <Download className="h-3.5 w-3.5" />
      </button>
    </>
  )
}
