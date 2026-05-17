import { AbsoluteFill } from "remotion";
import { linearTiming, TransitionSeries } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { SceneFadeWrapper } from "./components/SceneFadeWrapper";
import { ProgressDots } from "./components/ProgressDots";
import { TechGrid } from "./components/TechGrid";
import { Scene00Intro } from "./scenes/Scene00_Intro";
import { Scene01Landing } from "./scenes/Scene01_Landing";
import { Scene02Placement } from "./scenes/Scene02_Placement";
import { Scene03Clips } from "./scenes/Scene03_Clips";
import { Scene04Quiz } from "./scenes/Scene04_Quiz";
import { Scene05Speaking } from "./scenes/Scene05_Speaking";
import { Scene06Dashboard } from "./scenes/Scene06_Dashboard";
import { Scene07Teacher } from "./scenes/Scene07_TeacherOutro";
import { Scene08Outro } from "./scenes/Scene08_Outro";

const fadeTransition = fade();
const timing = linearTiming({ durationInFrames: 25 });

/**
 * 主视频序列。9 段 Scene，TransitionSeries crossfade。
 * 总时长 = 180s × 30fps = 5400 帧。
 */
export const MainVideo: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#FFFFFF" }}>
      <TransitionSeries>
        {/* Scene 0: 开场 — 8s (240f) */}
        <TransitionSeries.Sequence durationInFrames={240}>
          <SceneFadeWrapper><Scene00Intro /></SceneFadeWrapper>
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fadeTransition} timing={timing} />

        {/* Scene 1: 落地页 — 8s (240f) */}
        <TransitionSeries.Sequence durationInFrames={240}>
          <SceneFadeWrapper><Scene01Landing /></SceneFadeWrapper>
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fadeTransition} timing={timing} />

        {/* Scene 2: 定级测试 — 14s (420f) */}
        <TransitionSeries.Sequence durationInFrames={420}>
          <SceneFadeWrapper><Scene02Placement /></SceneFadeWrapper>
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fadeTransition} timing={timing} />

        {/* Scene 3: 影视片段 — 20s (600f) */}
        <TransitionSeries.Sequence durationInFrames={600}>
          <SceneFadeWrapper><Scene03Clips /></SceneFadeWrapper>
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fadeTransition} timing={timing} />

        {/* Scene 4: AI出题 — 20s (600f) */}
        <TransitionSeries.Sequence durationInFrames={600}>
          <SceneFadeWrapper><Scene04Quiz /></SceneFadeWrapper>
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fadeTransition} timing={timing} />

        {/* Scene 5: 口语评测 — 33s (990f) */}
        <TransitionSeries.Sequence durationInFrames={990}>
          <SceneFadeWrapper><Scene05Speaking /></SceneFadeWrapper>
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fadeTransition} timing={timing} />

        {/* Scene 6: 学习数据 — 23s (690f) */}
        <TransitionSeries.Sequence durationInFrames={690}>
          <SceneFadeWrapper><Scene06Dashboard /></SceneFadeWrapper>
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fadeTransition} timing={timing} />

        {/* Scene 7: 教师端 — 46s (1380f) */}
        <TransitionSeries.Sequence durationInFrames={1380}>
          <SceneFadeWrapper><Scene07Teacher /></SceneFadeWrapper>
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fadeTransition} timing={timing} />

        {/* Scene 8: 结尾 Outro — 8s (240f) */}
        <TransitionSeries.Sequence durationInFrames={240}>
          <SceneFadeWrapper><Scene08Outro /></SceneFadeWrapper>
        </TransitionSeries.Sequence>
      </TransitionSeries>
      <TechGrid />
      <ProgressDots />
    </AbsoluteFill>
  );
};
