import { useNotifications } from '~/context/NotificationContext'
import useAssistantName from '~/hooks/useAssistantName'
import { IconPhoto, IconSend, IconWand, IconX } from '@tabler/icons-react'
import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import classNames from '~/lib/classNames'
import { ChatImageAttachment, ChatMessage } from '../../../types/chat'
import type { ModelVisionCapability } from '../../../types/ollama'
import ChatMessageBubble from './ChatMessageBubble'
import ChatAssistantAvatar from './ChatAssistantAvatar'
import BouncingDots from '../BouncingDots'
import InfoTooltip from '../InfoTooltip'
import { visionAttachmentGuidance } from '../../lib/vision_guidance'

interface ChatInterfaceProps {
  messages: ChatMessage[]
  onSendMessage: (message: string, images: ChatImageAttachment[]) => void
  visionCapability: ModelVisionCapability
  isLoading?: boolean
  chatSuggestions?: string[]
  chatSuggestionsEnabled?: boolean
  chatSuggestionsLoading?: boolean
}

// Sent as an ordinary turn, so it goes through retrieval, budgeting and
// persistence like any other message. The cut-off answer is the newest turn in
// history, which the budget keeps first.
const CONTINUE_PROMPT = 'Continue exactly where you left off. Do not repeat what you already wrote.'

const MAX_VISION_IMAGES = 4
const MAX_VISION_IMAGE_BYTES = 8 * 1024 * 1024
const SUPPORTED_VISION_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])

export default function ChatInterface({
  messages,
  onSendMessage,
  visionCapability,
  isLoading = false,
  chatSuggestions = [],
  chatSuggestionsEnabled = false,
  chatSuggestionsLoading = false,
}: ChatInterfaceProps) {
  const { t } = useTranslation()
  const aiAssistantName = useAssistantName()
  const { addNotification } = useNotifications()
  const [input, setInput] = useState('')
  const [images, setImages] = useState<ChatImageAttachment[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)
  const previewUrlsRef = useRef<Set<string>>(new Set())

  useEffect(
    () => () => {
      previewUrlsRef.current.forEach((url) => URL.revokeObjectURL(url))
      previewUrlsRef.current.clear()
    },
    []
  )

  useEffect(() => {
    if (visionCapability !== 'unsupported') return
    setImages((current) => {
      current.forEach((image) => {
        URL.revokeObjectURL(image.previewUrl)
        previewUrlsRef.current.delete(image.previewUrl)
      })
      return []
    })
  }, [visionCapability])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if ((input.trim() || images.length > 0) && !isLoading) {
      onSendMessage(input.trim() || 'Describe the attached image.', images)
      setInput('')
      setImages([])
      if (imageInputRef.current) imageInputRef.current.value = ''
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleImageSelection = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(event.target.files ?? [])
    event.target.value = ''
    if (selected.length === 0) return

    const availableSlots = MAX_VISION_IMAGES - images.length
    if (availableSlots <= 0) {
      addNotification({
        type: 'error',
        message: t('chat:interface.tooManyImages', { max: MAX_VISION_IMAGES }),
      })
      return
    }

    const attachments: ChatImageAttachment[] = []
    for (const file of selected.slice(0, availableSlots)) {
      if (!SUPPORTED_VISION_TYPES.has(file.type)) {
        addNotification({
          type: 'error',
          message: t('chat:interface.unsupportedImage', { name: file.name }),
        })
        continue
      }
      if (file.size > MAX_VISION_IMAGE_BYTES) {
        addNotification({
          type: 'error',
          message: t('chat:interface.imageTooLarge', { name: file.name }),
        })
        continue
      }

      const previewUrl = URL.createObjectURL(file)
      previewUrlsRef.current.add(previewUrl)
      attachments.push({
        id: crypto.randomUUID(),
        name: file.name,
        file,
        previewUrl,
      })
    }

    if (selected.length > availableSlots) {
      addNotification({
        type: 'error',
        message: t('chat:interface.partiallyAttached', { count: availableSlots }),
      })
    }
    setImages((current) => [...current, ...attachments])
  }

  const removeImage = (image: ChatImageAttachment) => {
    URL.revokeObjectURL(image.previewUrl)
    previewUrlsRef.current.delete(image.previewUrl)
    setImages((current) => current.filter((item) => item.id !== image.id))
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    // Auto-resize textarea
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-surface-primary shadow-sm">
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center max-w-md">
              <IconWand className="h-16 w-16 text-desert-green mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-medium text-text-primary mb-2">
                {t('chat:interface.emptyTitle')}
              </h3>
              <p className="text-text-muted text-sm">{t('chat:interface.emptyDescription')}</p>
              {chatSuggestionsEnabled &&
                chatSuggestions &&
                chatSuggestions.length > 0 &&
                !chatSuggestionsLoading && (
                  <div className="mt-8">
                    <h4 className="text-sm font-medium text-text-secondary mb-2">
                      {t('chat:interface.suggestions')}
                    </h4>
                    <div className="flex flex-col gap-2">
                      {chatSuggestions.map((suggestion, index) => (
                        <button
                          key={index}
                          onClick={() => {
                            setInput(suggestion)
                            // Focus the textarea after setting input
                            setTimeout(() => {
                              textareaRef.current?.focus()
                            }, 0)
                          }}
                          className="px-4 py-2 bg-surface-secondary hover:bg-surface-secondary rounded-lg text-sm text-text-primary transition-colors"
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              {/* Display bouncing dots while loading suggestions */}
              {chatSuggestionsEnabled && chatSuggestionsLoading && (
                <BouncingDots text={t('chat:interface.thinking')} containerClassName="mt-8" />
              )}
              {!chatSuggestionsEnabled && (
                <div className="mt-8 text-sm text-text-muted">
                  {t('chat:interface.suggestionsDisabled')}
                </div>
              )}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, idx) => (
              <div
                key={message.id}
                className={classNames(
                  'flex gap-4',
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                )}
              >
                {message.role === 'assistant' && <ChatAssistantAvatar />}
                <ChatMessageBubble
                  message={message}
                  onContinue={
                    idx === messages.length - 1 && !isLoading
                      ? () => onSendMessage(CONTINUE_PROMPT, [])
                      : undefined
                  }
                />
              </div>
            ))}
            {/* Loading/thinking indicator */}
            {isLoading && (
              <div className="flex gap-4 justify-start">
                <ChatAssistantAvatar />
                <div className="max-w-[85%] sm:max-w-[70%] rounded-lg px-4 py-3 bg-surface-secondary text-text-primary">
                  <BouncingDots text={t('chat:interface.thinking')} />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>
      <div className="border-t border-border-subtle bg-surface-primary px-6 py-4 flex-shrink-0 min-h-[90px]">
        {images.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-3" aria-label={t('chat:interface.attachedImages')}>
            {images.map((image) => (
              <div
                key={image.id}
                className="relative h-20 w-20 overflow-hidden rounded-lg border border-border-default bg-surface-secondary"
              >
                <img src={image.previewUrl} alt={image.name} className="h-full w-full object-cover" />
                <button
                  type="button"
                  onClick={() => removeImage(image)}
                  className="absolute right-1 top-1 rounded-full bg-surface-primary/90 p-1 text-text-primary hover:bg-surface-primary"
                  aria-label={t('chat:interface.removeImage', { name: image.name })}
                  disabled={isLoading}
                >
                  <IconX className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </div>
            ))}
          </div>
        )}
        <form onSubmit={handleSubmit} className="flex gap-3 items-end">
          <input
            ref={imageInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            className="hidden"
            onChange={handleImageSelection}
          />
          <div className="mb-2 flex items-center">
            <button
              type="button"
              onClick={() => imageInputRef.current?.click()}
              disabled={
                isLoading ||
                images.length >= MAX_VISION_IMAGES ||
                visionCapability === 'unsupported'
              }
              className={classNames(
                'p-3 rounded-lg transition-colors flex-shrink-0',
                isLoading ||
                  images.length >= MAX_VISION_IMAGES ||
                  visionCapability === 'unsupported'
                  ? 'bg-border-default text-text-muted cursor-not-allowed'
                  : 'border border-border-default text-text-secondary hover:bg-surface-secondary'
              )}
              aria-label={t('chat:interface.attachImages')}
            >
              <IconPhoto className="h-6 w-6" aria-hidden="true" />
            </button>
            {visionCapability !== 'supported' && (
              <InfoTooltip
                position="top"
                align="left"
                text={
                  t(visionAttachmentGuidance(visionCapability))
                }
              />
            )}
          </div>
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder={t('chat:interface.placeholder', { name: aiAssistantName })}
              className="w-full resize-none rounded-lg border border-border-default px-4 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-desert-green focus:border-transparent disabled:bg-surface-secondary disabled:text-text-muted"
              rows={1}
              disabled={isLoading}
              style={{ maxHeight: '200px' }}
            />
          </div>
          <button
            type="submit"
            disabled={(!input.trim() && images.length === 0) || isLoading}
            className={classNames(
              'p-3 rounded-lg transition-all duration-200 flex-shrink-0 mb-2',
              (!input.trim() && images.length === 0) || isLoading
                ? 'bg-border-default text-text-muted cursor-not-allowed'
                : 'bg-desert-green text-white hover:bg-desert-green/90 hover:scale-105'
            )}
          >
            {isLoading ? (
              <div className="h-6 w-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <IconSend className="h-6 w-6" />
            )}
          </button>
        </form>
        <p className="mt-2 text-xs text-text-muted" aria-live="polite">
          {t(visionAttachmentGuidance(visionCapability))}
        </p>
      </div>
    </div>
  )
}
