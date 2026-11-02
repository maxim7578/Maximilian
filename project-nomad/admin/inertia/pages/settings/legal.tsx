import { Head } from '@inertiajs/react'
import SettingsLayout from '~/layouts/SettingsLayout'
import { useTranslation } from 'react-i18next'

export default function LegalPage() {
  const { t } = useTranslation()
  return (
    <SettingsLayout>
      <Head title={t('system:legal.pageTitle')} />
      <div className="xl:pl-72 w-full">
        <main className="px-12 py-6 max-w-4xl">
          <h1 className="text-4xl font-semibold mb-8">{t('system:legal.title')}</h1>

          {/* License Agreement */}
          <section className="mb-10">
            <h2 className="text-2xl font-semibold mb-4">{t('system:legal.licenseTitle')}</h2>
            <p className="text-text-primary mb-3">Copyright 2024-2026 Crosstalk Solutions, LLC</p>
            <p className="text-text-primary mb-3">
              Licensed under the Apache License, Version 2.0 (the &quot;License&quot;);
              you may not use this file except in compliance with the License.
              You may obtain a copy of the License at
            </p>
            <p className="text-text-primary mb-3">
              <a href="https://www.apache.org/licenses/LICENSE-2.0" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">https://www.apache.org/licenses/LICENSE-2.0</a>
            </p>
            <p className="text-text-primary">
              Unless required by applicable law or agreed to in writing, software
              distributed under the License is distributed on an &quot;AS IS&quot; BASIS,
              WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
              See the License for the specific language governing permissions and
              limitations under the License.
            </p>
          </section>

          {/* Third-Party Software */}
          <section className="mb-10">
            <h2 className="text-2xl font-semibold mb-4">{t('system:legal.thirdPartyTitle')}</h2>
            <p className="text-text-primary mb-4">
              {t('system:legal.thirdPartyIntro')}
            </p>
            <ul className="space-y-3 text-text-primary">
              <li>
                <strong>Kiwix</strong> - {t('system:legal.kiwixDescription')} (GPL-3.0 License)
                <br />
                <a href="https://kiwix.org" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">https://kiwix.org</a>
              </li>
              <li>
                <strong>Kolibri</strong> - {t('system:legal.kolibriDescription')} (MIT License)
                <br />
                <a href="https://learningequality.org/kolibri" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">https://learningequality.org/kolibri</a>
              </li>
              <li>
                <strong>Ollama</strong> - {t('system:legal.ollamaDescription')} (MIT License)
                <br />
                <a href="https://ollama.com" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">https://ollama.com</a>
              </li>
              <li>
                <strong>CyberChef</strong> - {t('system:legal.cyberchefDescription')} (Apache 2.0 License)
                <br />
                <a href="https://github.com/gchq/CyberChef" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">https://github.com/gchq/CyberChef</a>
              </li>
              <li>
                <strong>FlatNotes</strong> - {t('system:legal.flatnotesDescription')} (MIT License)
                <br />
                <a href="https://github.com/dullage/flatnotes" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">https://github.com/dullage/flatnotes</a>
              </li>
              <li>
                <strong>Qdrant</strong> - {t('system:legal.qdrantDescription')} (Apache 2.0 License)
                <br />
                <a href="https://github.com/qdrant/qdrant" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">https://github.com/qdrant/qdrant</a>
              </li>
            </ul>
          </section>

          {/* Privacy Statement */}
          <section className="mb-10">
            <h2 className="text-2xl font-semibold mb-4">{t('system:legal.privacyTitle')}</h2>
            <p className="text-text-primary mb-3">
              {t('system:legal.privacyIntro')}
            </p>
            <ul className="list-disc list-inside space-y-2 text-text-primary">
              <li><strong>{t('system:legal.zeroTelemetryLabel')}</strong> {t('system:legal.zeroTelemetryText')}</li>
              <li><strong>{t('system:legal.localFirstLabel')}</strong> {t('system:legal.localFirstText')}</li>
              <li><strong>{t('system:legal.noAccountsLabel')}</strong> {t('system:legal.noAccountsText')}</li>
              <li><strong>{t('system:legal.networkOptionalLabel')}</strong> {t('system:legal.networkOptionalText')}</li>
            </ul>
          </section>

          {/* Content Disclaimer */}
          <section className="mb-10">
            <h2 className="text-2xl font-semibold mb-4">{t('system:legal.contentDisclaimerTitle')}</h2>
            <p className="text-text-primary mb-3">
              {t('system:legal.contentDisclaimer1')}
            </p>
            <p className="text-text-primary mb-3">
              {t('system:legal.contentDisclaimer2')}
            </p>
            <p className="text-text-primary">
              {t('system:legal.contentDisclaimer3')}
            </p>
          </section>

          {/* Medical Disclaimer */}
          <section className="mb-10">
            <h2 className="text-2xl font-semibold mb-4">{t('system:legal.medicalTitle')}</h2>
            <p className="text-text-primary mb-3">
              {t('system:legal.medicalIntro')}
            </p>
            <p className="text-text-primary mb-3 font-semibold">
              {t('system:legal.medicalNotSubstitute')}
            </p>
            <ul className="list-disc list-inside space-y-2 text-text-primary mb-3">
              <li>{t('system:legal.medicalPoint1')}</li>
              <li>{t('system:legal.medicalPoint2')}</li>
              <li>{t('system:legal.medicalPoint3')}</li>
              <li>{t('system:legal.medicalPoint4')}</li>
            </ul>
          </section>

          {/* Data Storage Notice */}
          <section className="mb-10">
            <h2 className="text-2xl font-semibold mb-4">{t('system:legal.dataStorageTitle')}</h2>
            <p className="text-text-primary mb-3">
              {t('system:legal.dataStorageIntro')}
            </p>
            <ul className="list-disc list-inside space-y-2 text-text-primary">
              <li><strong>{t('system:legal.installationDirectoryLabel')}</strong> /opt/project-nomad</li>
              <li><strong>{t('system:legal.downloadedContentLabel')}</strong> /opt/project-nomad/storage</li>
              <li><strong>{t('system:legal.applicationDataLabel')}</strong> {t('system:legal.applicationDataText')}</li>
            </ul>
            <p className="text-text-primary mt-3">
              {t('system:legal.dataStorageControl')}
            </p>
          </section>

        </main>
      </div>
    </SettingsLayout>
  )
}
