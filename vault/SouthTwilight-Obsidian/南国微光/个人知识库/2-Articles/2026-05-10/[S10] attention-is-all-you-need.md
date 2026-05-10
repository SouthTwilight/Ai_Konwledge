---
title: Attention Is All You Need
source: https://arxiv.org/html/1706.03762v7
source_name: web
date_processed: '2026-05-10'
tags:
- llm
- research
- deep-learning
relevance: 10
level: l3
hash: c2939668526cd63b
---
# Attention Is All You Need

> Source: [web](https://arxiv.org/html/1706.03762v7)

## Summary

**TL;DR:** 提出Transformer架构，完全基于注意力机制，摒弃循环和卷积，显著提升训练并行化效率并在机器翻译任务中取得SOTA效果。

本文提出了Transformer模型，这是一种完全基于注意力机制的新型神经网络架构，摒弃了传统的循环和卷积结构。该模型通过编码器-解码器结构处理序列转换任务，利用自注意力机制捕捉输入和输出之间的全局依赖关系。Transformer的核心组件包括多头注意力机制和位置前馈网络，并采用残差连接和层归一化来稳定训练。由于不再依赖序列化的递归计算，模型在训练时具有极高的并行性，大幅缩短了训练时间。实验表明，在WMT 2014英德和英法翻译任务上，Transformer分别达到了28.4和41.8的BLEU分数，超越了当时的最佳模型。此外，该架构在英语成分句法分析任务中也表现出良好的泛化能力。这一工作奠定了现代大语言模型（LLM）的基础架构。

## Key Points

- Transformer是首个完全依赖自注意力机制而不使用序列对齐RNN或卷积的序列转换模型，彻底改变了序列建模的范式。
- 模型采用编码器-解码器架构，编码器由多层自注意力和前馈网络组成，解码器在此基础上增加了对编码器输出的注意力层。
- 引入了缩放点积注意力，通过计算Query与Key的点积并除以维度平方根来防止梯度消失，有效处理长序列依赖。
- 利用多头注意力机制允许模型在不同的位置共同关注来自不同子空间的信息，增强了模型捕捉复杂特征的能力。
- 通过位置编码将序列顺序信息注入模型，弥补了自注意力机制本身无法捕捉位置顺序的缺陷。
- 实验结果显示该模型在8个P100 GPU上仅需12小时训练即可达到顶尖翻译质量，证明了其极高的训练效率。

## Deep Analysis

**核心洞见:** 完全摒弃循环和卷积、仅依赖注意力机制的Transformer架构，能够以极高的并行化效率和更低的训练成本，在序列转换任务中达到当时的最佳性能。 

**文章类型:** research

**前提假设:**
- 传统的循环神经网络固有的序列计算特性是限制模型训练并行化和效率的根本瓶颈。
- 自注意力机制足以有效捕捉序列中任意距离的依赖关系，而不需要依赖递归或卷积的局部归纳偏置。
- 多头注意力能够弥补全局注意力平均化导致的分辨率降低问题，使模型能关注不同子空间的信息。

**作者立场:** 创新且自信的倡导者

**核心概念:**
- **Transformer架构**: 一种完全基于注意力机制、摒弃了传统的循环和卷积结构的编码器-解码器神经网络架构。
- **自注意力机制**: 一种将单一序列的不同位置联系起来以计算该序列表示的注意力机制，能够捕捉序列内部的全局依赖关系。
- **缩放点积注意力**: 通过计算查询和键的点积并除以维度的平方根进行缩放，再经过softmax函数获得权重以对值进行加权求和的注意力计算方法。
- **多头注意力**: 将注意力机制并行运行多次，每次使用不同的线性投影，使模型能够同时关注不同位置的不同表示子空间的信息。
- **位置编码**: 由于Transformer缺乏循环和卷积结构，通过注入序列中token的相对或绝对位置信息来弥补序列顺序感知能力的机制。
- **编码器-解码器结构**: 序列转换模型的通用范式，编码器将输入符号映射为连续表示，解码器基于此表示自回归地逐个生成输出符号。
- **掩码自注意力**: 在解码器的自注意力子层中使用的遮蔽技术，防止当前位置关注到后续位置的信息，以确保自回归生成的因果性。
- **残差连接与层归一化**: 在每个子层输出上先进行残差跳跃连接再进行层归一化的技术，用于稳定和加速深层网络的训练。

## Related

[[Deep Learning]] [[Natural Language Processing]] [[Neural Machine Translation]] [[Self-Attention Mechanism]]

## Tags

#llm #research #deep-learning

## 原文内容

Provided proper attribution is provided, Google hereby grants permission to reproduce the tables and figures in this paper solely for use in journalistic or scholarly works.
Attention Is All You Need
Abstract
The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles, by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs, a small fraction of the training costs of the best models from the literature. We show that the Transformer generalizes well to other tasks by applying it successfully to English constituency parsing both with large and limited training data.
1 Introduction
Recurrent neural networks, long short-term memory [[13](#bib.bib13)] and gated recurrent [[7](#bib.bib7)] neural networks in particular, have been firmly established as state of the art approaches in sequence modeling and transduction problems such as language modeling and machine translation [[35](#bib.bib35), [2](#bib.bib2), [5](#bib.bib5)]. Numerous efforts have since continued to push the boundaries of recurrent language models and encoder-decoder architectures [[38](#bib.bib38), [24](#bib.bib24), [15](#bib.bib15)].
Recurrent models typically factor computation along the symbol positions of the input and output sequences. Aligning the positions to steps in computation time, they generate a sequence of hidden states , as a function of the previous hidden state and the input for position . This inherently sequential nature precludes parallelization within training examples, which becomes critical at longer sequence lengths, as memory constraints limit batching across examples.
Recent work has achieved significant improvements in computational efficiency through factorization tricks [[21](#bib.bib21)] and conditional computation [[32](#bib.bib32)], while also improving model performance in case of the latter. The fundamental constraint of sequential computation, however, remains.
Attention mechanisms have become an integral part of compelling sequence modeling and transduction models in various tasks, allowing modeling of dependencies without regard to their distance in the input or output sequences [[2](#bib.bib2), [19](#bib.bib19)]. In all but a few cases [[27](#bib.bib27)], however, such attention mechanisms are used in conjunction with a recurrent network.
In this work we propose the Transformer, a model architecture eschewing recurrence and instead relying entirely on an attention mechanism to draw global dependencies between input and output. The Transformer allows for significantly more parallelization and can reach a new state of the art in translation quality after being trained for as little as twelve hours on eight P100 GPUs.
2 Background
The goal of reducing sequential computation also forms the foundation of the Extended Neural GPU [[16](#bib.bib16)], ByteNet [[18](#bib.bib18)] and ConvS2S [[9](#bib.bib9)], all of which use convolutional neural networks as basic building block, computing hidden representations in parallel for all input and output positions. In these models, the number of operations required to relate signals from two arbitrary input or output positions grows in the distance between positions, linearly for ConvS2S and logarithmically for ByteNet. This makes it more difficult to learn dependencies between distant positions [[12](#bib.bib12)]. In the Transformer this is reduced to a constant number of operations, albeit at the cost of reduced effective resolution due to averaging attention-weighted positions, an effect we counteract with Multi-Head Attention as described in section [3.2](#S3.SS2).
Self-attention, sometimes called intra-attention is an attention mechanism relating different positions of a single sequence in order to compute a representation of the sequence. Self-attention has been used successfully in a variety of tasks including reading comprehension, abstractive summarization, textual entailment and learning task-independent sentence representations [[4](#bib.bib4), [27](#bib.bib27), [28](#bib.bib28), [22](#bib.bib22)].
End-to-end memory networks are based on a recurrent attention mechanism instead of sequence-aligned recurrence and have been shown to perform well on simple-language question answering and language modeling tasks [[34](#bib.bib34)].
To the best of our knowledge, however, the Transformer is the first transduction model relying entirely on self-attention to compute representations of its input and output without using sequence-aligned RNNs or convolution.
In the following sections, we will describe the Transformer, motivate self-attention and discuss its advantages over models such as [[17](#bib.bib17), [18](#bib.bib18)] and [[9](#bib.bib9)].
3 Model Architecture
Most competitive neural sequence transduction models have an encoder-decoder structure [[5](#bib.bib5), [2](#bib.bib2), [35](#bib.bib35)]. Here, the encoder maps an input sequence of symbol representations to a sequence of continuous representations . Given , the decoder then generates an output sequence of symbols one element at a time. At each step the model is auto-regressive [[10](#bib.bib10)], consuming the previously generated symbols as additional input when generating the next.
The Transformer follows this overall architecture using stacked self-attention and point-wise, fully connected layers for both the encoder and decoder, shown in the left and right halves of Figure [1](#S3.F1), respectively.
3.1 Encoder and Decoder Stacks
Encoder:
The encoder is composed of a stack of identical layers. Each layer has two sub-layers. The first is a multi-head self-attention mechanism, and the second is a simple, position-wise fully connected feed-forward network. We employ a residual connection [[11](#bib.bib11)] around each of the two sub-layers, followed by layer normalization [[1](#bib.bib1)]. That is, the output of each sub-layer is , where is the function implemented by the sub-layer itself. To facilitate these residual connections, all sub-layers in the model, as well as the embedding layers, produce outputs of dimension .
Decoder:
The decoder is also composed of a stack of identical layers. In addition to the two sub-layers in each encoder layer, the decoder inserts a third sub-layer, which performs multi-head attention over the output of the encoder stack. Similar to the encoder, we employ residual connections around each of the sub-layers, followed by layer normalization. We also modify the self-attention sub-layer in the decoder stack to prevent positions from attending to subsequent positions. This masking, combined with fact that the output embeddings are offset by one position, ensures that the predictions for position can depend only on the known outputs at positions less than .
3.2 Attention
An attention function can be described as mapping a query and a set of key-value pairs to an output, where the query, keys, values, and output are all vectors. The output is computed as a weighted sum of the values, where the weight assigned to each value is computed by a compatibility function of the query with the corresponding key.
3.2.1 Scaled Dot-Product Attention
We call our particular attention "Scaled Dot-Product Attention" (Figure [2](#S3.F2)). The input consists of queries and keys of dimension , and values of dimension . We compute the dot products of the query with all keys, divide each by , and apply a softmax function to obtain the weights on the values.
In practice, we [...truncated]


## Personal Notes
