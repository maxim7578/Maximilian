import { useTranslation } from 'react-i18next'

type ScaleUnit = 'imperial' | 'metric' | 'nautical'

type ScaleUnitSelectorProps = {
    scaleUnit: ScaleUnit
    onChange: (unit: ScaleUnit) => void
    onMouseEnter?: () => void
}

export default function ScaleUnitSelector({
                                          scaleUnit,
                                          onChange,
                                          onMouseEnter,
                                        }: ScaleUnitSelectorProps) {
  const { t } = useTranslation()
  return (
    <div className="absolute bottom-[30px] left-[10px] z-[2]" onMouseEnter={onMouseEnter}>
      <div className="inline-flex overflow-hidden rounded text-[11px] font-semibold leading-none shadow-[0_0_0_2px_rgba(0,0,0,0.1)]">

        {/* Metric */}
        <button
          type="button"
          onClick={() => {
            if (scaleUnit !== 'metric') onChange('metric')
          }}
          className="border-0 px-2 py-1"
          style={{
            background: scaleUnit === 'metric' ? '#424420' : 'white',
            color: scaleUnit === 'metric' ? 'white' : '#666',
            cursor: 'pointer',
          }}
        >
          {t('maps:scaleUnits.metric')}
        </button>

        {/* Imperial */}
        <button
          type="button"
          onClick={() => {
            if (scaleUnit !== 'imperial') onChange('imperial')
          }}
          className="border-0 px-2 py-1"
          style={{
            background: scaleUnit === 'imperial' ? '#424420' : 'white',
            color: scaleUnit === 'imperial' ? 'white' : '#666',
            cursor: 'pointer',
          }}
        >
          {t('maps:scaleUnits.imperial')}
        </button>

        {/* Nautical */}
        <button
          type="button"
          onClick={() => {
            if (scaleUnit !== 'nautical') onChange('nautical')
          }}
          className="border-0 px-2 py-1"
          style={{
            background: scaleUnit === 'nautical' ? '#424420' : 'white',
            color: scaleUnit === 'nautical' ? 'white' : '#666',
            cursor: 'pointer',
          }}
        >
          {t('maps:scaleUnits.nautical')}
        </button>

      </div>
    </div>
  )
}
