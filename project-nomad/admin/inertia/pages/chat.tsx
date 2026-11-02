import useAssistantName from '~/hooks/useAssistantName'
import { Head } from '@inertiajs/react'
import ChatComponent from '~/components/chat'

export default function Chat(props: { settings: { chatSuggestionsEnabled: boolean } }) {
  const aiAssistantName = useAssistantName()
  return (
    <div className="w-full h-full">
      <Head title={aiAssistantName} />
      <ChatComponent enabled={true} suggestionsEnabled={props.settings.chatSuggestionsEnabled} />
    </div>
  )
}
