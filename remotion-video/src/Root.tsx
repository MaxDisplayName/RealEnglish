import { Composition } from "remotion";
import { MainVideo } from "./MainVideo";

export const Root: React.FC = () => {
  return (
    <Composition
      id="MainVideo"
      component={MainVideo}
      durationInFrames={5400} // 180s × 30fps
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
