import { StoryWorkspace } from '../story-workspace';
export default async function StoryPage({params}:{params:Promise<{trackId:string}>}) {
  return <StoryWorkspace trackId={(await params).trackId}/>;
}
