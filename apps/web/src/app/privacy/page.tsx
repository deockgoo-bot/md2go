export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-2xl font-bold text-gray-900 mb-8">개인정보처리방침</h1>

        <div className="prose prose-gray prose-sm max-w-none space-y-8 text-gray-700 leading-relaxed">

          <p className="text-gray-500">시행일: 2026년 3월 31일</p>

          <section>
            <h2 className="text-lg font-semibold text-gray-900">1. 개인정보의 처리 목적</h2>
            <p>HWP Converter AI(이하 &quot;서비스&quot;)는 다음 목적으로 개인정보를 처리합니다.</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>문의 접수 및 답변: 이메일, 이름</li>
              <li>서비스 남용 방지: IP 주소 기반 사용량 제한</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900">2. 수집하는 개인정보 항목</h2>
            <table className="w-full text-sm border border-gray-200">
              <thead>
                <tr className="bg-gray-50">
                  <th className="border border-gray-200 px-3 py-2 text-left">항목</th>
                  <th className="border border-gray-200 px-3 py-2 text-left">수집 정보</th>
                  <th className="border border-gray-200 px-3 py-2 text-left">보관 기간</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="border border-gray-200 px-3 py-2">문의하기</td>
                  <td className="border border-gray-200 px-3 py-2">이름(선택), 이메일</td>
                  <td className="border border-gray-200 px-3 py-2">답변 완료 후 1년</td>
                </tr>
                <tr>
                  <td className="border border-gray-200 px-3 py-2">사용량 제한</td>
                  <td className="border border-gray-200 px-3 py-2">IP 주소</td>
                  <td className="border border-gray-200 px-3 py-2">당일 자정 자동 삭제</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900">3. 업로드 문서 처리</h2>
            <p>서비스에 업로드되는 HWP·HWPX 파일 및 변환 결과 파일은 다음과 같이 처리됩니다.</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>업로드된 파일은 변환 처리 후 <strong>즉시 삭제</strong>됩니다.</li>
              <li>변환 결과 파일은 다운로드 후 삭제되며, 미다운로드 시 <strong>최대 1시간 내 자동 삭제</strong>됩니다.</li>
              <li>서버에 문서를 영구 저장하지 않습니다.</li>
              <li>업로드된 문서의 내용을 열람, 분석, 학습에 사용하지 않습니다.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900">4. AI 처리</h2>
            <p>AI 초안 생성, 교정, 검색 기능 사용 시 텍스트가 AWS Bedrock(Claude)에 전달됩니다.</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>AWS Bedrock은 입력 데이터를 모델 학습에 사용하지 않습니다.</li>
              <li>전달된 텍스트는 처리 후 보관되지 않습니다.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900">5. 개인정보의 제3자 제공</h2>
            <p>서비스는 이용자의 개인정보를 제3자에게 제공하지 않습니다. 단, 다음의 경우는 예외로 합니다.</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>법령에 의한 요청이 있는 경우</li>
              <li>이용자가 사전에 동의한 경우</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900">6. 개인정보의 파기</h2>
            <ul className="list-disc pl-5 space-y-1">
              <li>문의 정보: 답변 완료 후 1년 경과 시 파기</li>
              <li>IP 주소 (rate limit): 매일 자정(KST) 자동 삭제</li>
              <li>업로드 파일: 변환 즉시 또는 최대 1시간 내 삭제</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900">7. 이용자의 권리</h2>
            <p>이용자는 언제든지 다음 권리를 행사할 수 있습니다.</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>문의 정보의 열람, 수정, 삭제 요청</li>
              <li>개인정보 처리 정지 요청</li>
            </ul>
            <p>위 요청은 문의하기 페이지를 통해 가능합니다.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900">8. 쿠키 및 추적</h2>
            <p>서비스는 쿠키, 웹 비콘, 분석 도구를 사용하지 않습니다. 별도의 사용자 추적을 하지 않습니다.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900">9. 개인정보 보호책임자</h2>
            <p>문의하기 페이지를 통해 연락해 주시기 바랍니다.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900">10. 방침 변경</h2>
            <p>본 방침은 법령 또는 서비스 변경에 따라 수정될 수 있으며, 변경 시 웹사이트를 통해 공지합니다.</p>
          </section>

        </div>
      </div>
    </div>
  );
}
